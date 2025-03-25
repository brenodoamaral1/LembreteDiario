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
    for lembrete in lembretes:
        canal = bot.get_channel(lembrete["canal_id"])
        data_envio = datetime.strptime(lembrete["data_envio"], "%d/%m/%Y %H:%M:%S")
        conteudo = lembrete["mensagem"]
        agendar_mensagem(data_envio, canal, conteudo)

    await tree.sync()
    print(f"✅ Bot conectado como {bot.user}")

@tree.command(name="lembrete", description="Agende um lembrete para uma data e horário específico")
@app_commands.describe(
    data="Data do lembrete no formato DD/MM/AAAA",
    hora="Horário do lembrete no formato HH:MM (24h)",
    titulo="Título do lembrete",
    mensagem="Mensagem complementar"
)
async def lembrete(interaction: discord.Interaction, data: str, hora: str, titulo: str, mensagem: str):
    try:
        try:
            data_hora = parser.parse(f"{data.strip()} {hora.strip()}", dayfirst=True)
        except Exception:
            await interaction.response.send_message("❌ Data ou hora inválida. Use os formatos DD/MM/AAAA e HH:MM (ex: 25/03/2025 20:00)", ephemeral=True)
            return

        agora = datetime.now()
        if data_hora < agora:
            await interaction.response.send_message("❌ A data e hora precisam ser no futuro.", ephemeral=True)
            return

        canal = interaction.channel
        lembretes_salvos = carregar_lembretes()

        # Agendar mensagens
        horarios = [
            (data_hora - timedelta(hours=1), f"⏰ **{titulo}** começa em 1 hora!\n🎲 {mensagem}"),
            (data_hora - timedelta(minutes=30), f"⏰ **{titulo}** começa em 30 minutos!\n🎲 {mensagem}"),
            (data_hora, f"🚨 **{titulo}** está começando agora!\n🎲 {mensagem}")
        ]

        for horario, conteudo in horarios:
            if horario > agora:
                agendar_mensagem(horario, canal, conteudo)
                lembretes_salvos.append({
                    "data_envio": horario.strftime("%d/%m/%Y %H:%M:%S"),
                    "mensagem": conteudo,
                    "canal_id": canal.id
                })

        salvar_lembretes(lembretes_salvos)

        await interaction.response.send_message(
            f"✅ Lembrete agendado para {data_hora.strftime('%d/%m/%Y às %H:%M')} com o título: '{titulo}'",
            ephemeral=False
        )

    except Exception as e:
        await interaction.response.send_message(f"❌ Erro inesperado: {e}", ephemeral=True)

@tree.command(name="editar_lembrete", description="Edita um lembrete existente pela data e nova mensagem")
@app_commands.describe(
    data="Data do lembrete que deseja editar (DD/MM/AAAA)",
    nova_mensagem="Nova mensagem para esse lembrete"
)
async def editar_lembrete(interaction: discord.Interaction, data: str, nova_mensagem: str):
    try:
        data_formatada = parser.parse(data.strip(), dayfirst=True).strftime("%d/%m/%Y")
        lembretes = carregar_lembretes()
        editados = 0

        for lembrete in lembretes:
            if lembrete["data_envio"].startswith(data_formatada):
                lembrete["mensagem"] = nova_mensagem
                editados += 1

        if editados > 0:
            salvar_lembretes(lembretes)
            await interaction.response.send_message(f"✅ {editados} lembrete(s) editado(s) com sucesso.", ephemeral=False)
        else:
            await interaction.response.send_message("❌ Nenhum lembrete encontrado para essa data.", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao editar: {e}", ephemeral=True)

@tree.command(name="apagar_lembrete", description="Remove todos os lembretes agendados para uma data específica")
@app_commands.describe(
    data="Data do lembrete que deseja apagar (DD/MM/AAAA)"
)
async def apagar_lembrete(interaction: discord.Interaction, data: str):
    try:
        data_formatada = parser.parse(data.strip(), dayfirst=True).strftime("%d/%m/%Y")
        lembretes = carregar_lembretes()
        novos = [l for l in lembretes if not l["data_envio"].startswith(data_formatada)]
        removidos = len(lembretes) - len(novos)

        if removidos > 0:
            salvar_lembretes(novos)
            await interaction.response.send_message(f"✅ {removidos} lembrete(s) removido(s) com sucesso.", ephemeral=False)
        else:
            await interaction.response.send_message("❌ Nenhum lembrete encontrado para essa data.", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"❌ Erro ao apagar: {e}", ephemeral=True)

@tree.command(name="testar_mensagem", description="Envia uma mensagem de teste agora")
@app_commands.describe(
    titulo="Título da mensagem de teste",
    mensagem="Mensagem complementar"
)
async def testar_mensagem(interaction: discord.Interaction, titulo: str, mensagem: str):
    canal = interaction.channel
    conteudo = f"📢 **{titulo}**\n🎲 {mensagem}\n(mensagem de teste)"
    await canal.send(conteudo)
    await interaction.response.send_message("✅ Mensagem enviada!", ephemeral=True)

bot.run(TOKEN)
