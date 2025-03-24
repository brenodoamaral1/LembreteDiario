import discord
from discord.ext.commands import Bot
from discord import app_commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import asyncio
import os
import json
from dateutil import parser

TOKEN = os.environ.get("BOT_TOKEN")
CANAL_ID = 717521046642622508
LEMBRETES_FILE = "lembretes.json"

intents = discord.Intents.default()
bot = Bot(command_prefix="!", intents=intents)
tree = bot.tree
scheduler = AsyncIOScheduler()

# Função auxiliar para carregar lembretes do arquivo
def carregar_lembretes():
    if os.path.exists(LEMBRETES_FILE):
        with open(LEMBRETES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# Função auxiliar para salvar lembretes no arquivo
def salvar_lembretes(lembretes):
    with open(LEMBRETES_FILE, "w", encoding="utf-8") as f:
        json.dump(lembretes, f, ensure_ascii=False, indent=2)

# Função para agendar mensagem
def agendar_mensagem(data_envio: datetime, canal, conteudo: str):
    loop = asyncio.get_event_loop()
    scheduler.add_job(
        lambda: asyncio.run_coroutine_threadsafe(canal.send(conteudo), loop),
        trigger='date',
        run_date=data_envio
    )

@bot.event
async def on_ready():
    if not scheduler.running:
        scheduler.start()

    lembretes = carregar_lembretes()
    canal = bot.get_channel(CANAL_ID)
    for lembrete in lembretes:
        data_envio = datetime.strptime(lembrete["data_envio"], "%d/%m/%Y %H:%M:%S")
        conteudo = lembrete["mensagem"]
        agendar_mensagem(data_envio, canal, conteudo)

    await tree.sync()
    print(f"✅ Bot conectado como {bot.user}")

@tree.command(name="lembrete", description="Agende lembretes diários até a data escolhida")
@app_commands.describe(
    data="Data final do lembrete no formato DD/MM/AAAA",
    titulo="Título do lembrete",
    mensagem="Mensagem complementar"
)
async def lembrete(interaction: discord.Interaction, data: str, titulo: str, mensagem: str):
    try:
        try:
            data_lembrete = parser.parse(data.strip(), dayfirst=True)
        except Exception:
            await interaction.response.send_message("❌ Data inválida. Use o formato DD/MM/AAAA (ex: 25/03/2025)", ephemeral=True)
            return

        hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if data_lembrete < hoje:
            await interaction.response.send_message("❌ A data precisa ser no futuro.", ephemeral=True)
            return

        canal = bot.get_channel(CANAL_ID)
        if not canal:
            await interaction.response.send_message("❌ Canal não encontrado. Verifique as permissões do bot.", ephemeral=True)
            return

        lembretes_salvos = carregar_lembretes()
        dias = (data_lembrete - hoje).days

        for i in range(dias + 1):
            data_envio = hoje + timedelta(days=i)
            hora_envio = data_envio.replace(hour=12, minute=30, second=0)

            if i == dias:
                conteudo = f"📢 **Lembrete Diário! {titulo}**\n🎲 {mensagem}\nHOJE!!"
            elif i == dias - 1:
                conteudo = f"📢 **Lembrete Diário! {titulo}**\n🎲 {mensagem}\nAMANHÃ!"
            else:
                faltam = dias - i
                conteudo = f"📢 **Lembrete Diário! {titulo}**\n🎲 {mensagem}\nFaltam **{faltam}** dia{'s' if faltam > 1 else ''}!"

            agendar_mensagem(hora_envio, canal, conteudo)
            lembretes_salvos.append({
                "data_envio": hora_envio.strftime("%d/%m/%Y %H:%M:%S"),
                "mensagem": conteudo
            })

        salvar_lembretes(lembretes_salvos)

        await interaction.response.send_message(
            f"✅ Lembretes diários agendados até {data_lembrete.strftime('%d/%m/%Y')} com o título: '{titulo}'",
            ephemeral=False
        )

    except Exception as e:
        await interaction.response.send_message(f"❌ Erro inesperado: {e}", ephemeral=True)

@tree.command(name="testar_mensagem", description="Envia uma mensagem de teste agora")
@app_commands.describe(
    titulo="Título da mensagem de teste",
    mensagem="Mensagem complementar"
)
async def testar_mensagem(interaction: discord.Interaction, titulo: str, mensagem: str):
    canal = bot.get_channel(CANAL_ID)
    if canal:
        conteudo = f"📢 **{titulo}**\n🎲 {mensagem}\n(mensagem de teste)"
        await canal.send(conteudo)
        await interaction.response.send_message("✅ Mensagem enviada!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Canal não encontrado.", ephemeral=True)

bot.run(TOKEN)
