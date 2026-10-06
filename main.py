import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from discord.ext import commands
from google import genai
from openai import OpenAI

# --- 1. SERVER GIẢ CHO RENDER ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot AI is running!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- 2. KHỞI TẠO BOT & LẤY KEYS ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

GEMINI_KEYS = []
g_key1 = os.getenv("GEMINI_API_KEY_1")
g_key2 = os.getenv("GEMINI_API_KEY_2")
if g_key1: GEMINI_KEYS.append(g_key1.strip())
if g_key2: GEMINI_KEYS.append(g_key2.strip())
if not GEMINI_KEYS:
    old_key = os.getenv("GEMINI_API_KEY")
    if old_key: GEMINI_KEYS.append(old_key.strip())

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
user_models = {}

SYSTEM_PROMPT = (
    "Bạn là một trợ lý AI cá nhân thông minh, am hiểu sâu sắc về công nghệ, phần cứng, lập trình, "
    "và hệ thống Android/Linux. Hãy luôn suy luận cẩn thận, chi tiết, cung cấp giải pháp chính xác "
    "và hữu ích nhất. Trả lời bằng tiếng Việt thân thiện, tự nhiên, trình bày đẹp mắt bằng Markdown."
)

# --- 3. HÀM ĐIỀU HƯỚNG GỌI AI ---
def ask_ai(prompt, model_name):
    # Nhóm Gemini
    if model_name.startswith("gemini"):
        last_exception = None
        for key in GEMINI_KEYS:
            try:
                client = genai.Client(api_key=key)
                res = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.7
                    )
                )
                return res.text
            except Exception as e:
                last_exception = e
        raise last_exception or Exception("Không có Gemini API Key hợp lệ.")

    # Nhóm ChatGPT (OpenAI)
    else:
        if not OPENAI_KEY:
            raise Exception("Chưa cài đặt OPENAI_API_KEY trên Render!")
        
        client = OpenAI(api_key=OPENAI_KEY)
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content

# --- 4. SỰ KIỆN BOT ONLINE ---
@bot.event
async def on_ready():
    custom_status = discord.CustomActivity(name="Chat AI (Gemini & ChatGPT) ✨")
    await bot.change_presence(activity=custom_status)
    try:
        synced = await bot.tree.sync()
        print(f"✅ Đã sync {len(synced)} lệnh slash command!")
    except Exception as e:
        print(f"⚠️ Lỗi sync command: {e}")
    print(f"🚀 Bot đã online!")

# --- 5. SLASH COMMAND CHỌN MODEL AI ---
@bot.tree.command(name="model", description="Chọn model Gemini hoặc ChatGPT")
@app_commands.choices(selected_model=[
    # Gemini Models
    app_commands.Choice(name="[Gemini] 3.5 Flash-Lite", value="gemini-3.5-flash-lite"),
    app_commands.Choice(name="[Gemini] 3.6 Flash", value="gemini-3.6-flash"),
    
    # ChatGPT Models
    app_commands.Choice(name="[ChatGPT] 6 Astra", value="gpt-6-astra"),
    app_commands.Choice(name="[ChatGPT] 6 Sol", value="gpt-6-sol"),
    app_commands.Choice(name="[ChatGPT] GPT 5.5", value="gpt-5.5"),
    app_commands.Choice(name="[ChatGPT] GPT 5.5 Pro", value="gpt-5.5-pro"),
    app_commands.Choice(name="[ChatGPT] GPT 5.4 Mini", value="gpt-5.4-mini"),
])
async def set_model(interaction: discord.Interaction, selected_model: app_commands.Choice[str]):
    user_models[interaction.user.id] = selected_model.value
    await interaction.response.send_message(
        f"✅ Đã chuyển model sang: **{selected_model.name}** (`{selected_model.value}`)",
        ephemeral=True
    )

# --- 6. XỬ LÝ CHAT VỚI AI ---
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message) or message.content.startswith('!ask'):
        prompt = message.content.replace(f'<@{bot.user.id}>', '').replace('!ask', '').strip()

        if not prompt:
            await message.channel.send("Nhập câu hỏi nữa bro!")
            return

        current_model = user_models.get(message.author.id, "gemini-3.6-flash")

        async with message.channel.typing():
            try:
                reply = ask_ai(prompt, current_model)

                if len(reply) > 2000:
                    for i in range(0, len(reply), 1900):
                        await message.reply(reply[i:i+1900])
                else:
                    await message.reply(reply)

            except Exception as e:
                await message.channel.send(f"❌ Lỗi xử lý AI: {e}")

    await bot.process_commands(message)

# --- 7. CHẠY BOT ---
bot.run(DISCORD_TOKEN)
