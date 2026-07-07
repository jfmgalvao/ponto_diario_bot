import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from src.models import init_db, User, Ponto, get_now_sp

load_dotenv()

# Configuração de Logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /iniciar NOME_EMPRESA
    """
    telegram_id = str(update.effective_user.id)
    nome = update.effective_user.first_name
    
    args = context.args
    if not args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Por favor, informe o nome da empresa. Exemplo: /iniciar MINHA_EMPRESA"
        )
        return
        
    empresa = " ".join(args)
    
    try:
        user, created = User.get_or_create(
            telegram_id=telegram_id,
            defaults={'nome': nome, 'empresa': empresa}
        )
        
        if created:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f"Bem-vindo(a) {nome}! Você foi cadastrado(a) na empresa {empresa}."
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f"Olá {nome}! Você já está cadastrado(a) na empresa {user.empresa}."
            )
    except Exception as e:
        logging.error(f"Erro no banco de dados: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Erro interno. Tente novamente mais tarde."
        )

async def bater_ponto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /bater_ponto (ou /ponto)
    """
    telegram_id = str(update.effective_user.id)
    
    try:
        user = User.get(User.telegram_id == telegram_id)
    except User.DoesNotExist:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Você ainda não está cadastrado! Use /iniciar NOME_EMPRESA primeiro."
        )
        return
        
    agora = get_now_sp()
    hoje = agora.date()
    
    # Busca o último ponto do dia para esse usuário
    ultimo_ponto = (Ponto.select()
                    .where(
                        (Ponto.telegram_id == telegram_id) & 
                        (Ponto.data_hora >= hoje)
                    )
                    .order_by(Ponto.data_hora.desc())
                    .first())
                    
    # Lógica de Entrada/Saída alternada
    if not ultimo_ponto or ultimo_ponto.tipo == 'saida':
        tipo = 'entrada'
    else:
        tipo = 'saida'
        
    # Registra o novo ponto
    Ponto.create(
        telegram_id=telegram_id,
        empresa=user.empresa,
        tipo=tipo,
        data_hora=agora
    )
    
    hora_formatada = agora.strftime("%d/%m/%Y %H:%M:%S")
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=f"✅ Ponto de *{tipo.upper()}* registrado com sucesso às {hora_formatada}!",
        parse_mode="Markdown"
    )

import pandas as pd
from datetime import timedelta

async def relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /relatorio
    Gera uma planilha Excel com os pontos da empresa do usuário solicitante nos últimos 7 dias.
    """
    telegram_id = str(update.effective_user.id)
    
    try:
        user = User.get(User.telegram_id == telegram_id)
    except User.DoesNotExist:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Você não está cadastrado!")
        return
        
    agora = get_now_sp()
    sete_dias_atras = agora - timedelta(days=7)
    
    pontos = Ponto.select(Ponto, User).join(User, on=(Ponto.telegram_id == User.telegram_id)).where(
        (Ponto.empresa == user.empresa) &
        (Ponto.data_hora >= sete_dias_atras)
    ).order_by(Ponto.data_hora)
    
    if not pontos:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Nenhum ponto registrado nos últimos 7 dias.")
        return
        
    data = []
    for p in pontos:
        data.append({
            "Funcionário": p.user.nome,
            "Empresa": p.empresa,
            "Tipo": p.tipo.upper(),
            "Data e Hora": p.data_hora.strftime("%d/%m/%Y %H:%M:%S")
        })
        
    df = pd.DataFrame(data)
    filename = f"relatorio_{user.empresa}_{agora.strftime('%Y%m%d%H%M')}.xlsx"
    df.to_excel(filename, index=False)
    
    with open(filename, 'rb') as f:
        await context.bot.send_document(
            chat_id=update.effective_chat.id, 
            document=f, 
            filename=filename,
            caption="📊 Aqui está o relatório de ponto dos últimos 7 dias da sua empresa."
        )
    os.remove(filename)

if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == 'seu_token_aqui':
        print("ERRO: TELEGRAM_BOT_TOKEN não configurado no .env")
        exit(1)
        
    # Inicializa as tabelas no Supabase (se não existirem)
    init_db()
        
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('iniciar', start))
    application.add_handler(CommandHandler('bater_ponto', bater_ponto))
    application.add_handler(CommandHandler('ponto', bater_ponto))
    application.add_handler(CommandHandler('relatorio', relatorio))
    
    print("Bot rodando! Pressione Ctrl+C para parar.")
    application.run_polling()
