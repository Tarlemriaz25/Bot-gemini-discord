import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from discord.ext import commands
from google import genai

# --- 1. MỞ PORT GIẢ CHO RENDER ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- 2. KHỞI TẠO BOT & GEMINI ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Bộ nhớ lưu model được chọn của từng User (Mặc định là gemini-2.0-flash)
user_models = {}

@bot.event
async def on_ready():
    # Sync các Slash Command (dấu /) với Discord
    try:
        synced = await bot.tree.sync()
        print(f"Đã sync {len(synced)} lệnh slash command!")
    except Exception as e:
        print(f"Lỗi sync command: {e}")
    print(f"Bot đã online: {bot.user}")

# --- 3. SLASH COMMAND: /model ---
@bot.tree.command(name="model", description="Chọn model Gemini bro muốn dùng")
@app_commands.choices(selected_model=[
    app_commands.Choice(name="Gemini 3.6 Flash (Nhanh & Chuẩn - Mặc định)", value="gemini-3.6-flash"),
    app_commands.Choice(name="Gemini 3.5 Flash-Lite (Ổn định)", value="gemini-3.5-flash-lite"),
    app_commands.Choice(name="Gemini 3.7 Flash (Thông minh hơn)", value="gemini-3.7-flash"),
])
async def set_model(interaction: discord.Interaction, selected_model: app_commands.Choice[str]):
    user_models[interaction.user.id] = selected_model.value
    await interaction.response.send_message(
        f"✅ Đã đổi model cho bro **{interaction.user.name}** thành: `{selected_model.value}`!",
        ephemeral=True # Chỉ người bấm lệnh mới thấy tin nhắn này
    )
# --- HÀM GỌI API GEMINI VỚI SYSTEM PROMPT GIÚP BOT THÔNG MINH HƠN ---
def generate_content_with_fallback(prompt, model_name):
    last_exception = None
    
    # SYSTEM INSTRUCTION: "Thổi hồn" và tăng trí thông minh cho Bot ở đây!
    system_instruction = (
        "Bạn là một trợ lý AI cá nhân thông minh, am hiểu sâu sắc về công nghệ, phần cứng, lập trình, "
        "và hệ thống Android/Linux. Hãy luôn suy luận cẩn thận, chi tiết, cung cấp giải pháp chính xác "
        "và hữu ích nhất. Trả lời bằng tiếng Việt thân thiện, tự nhiên, trình bày đẹp mắt bằng Markdown "
        "(dùng bullet points, codeblock khi cần)."
    )
    
    for idx, key in enumerate(API_KEYS):
        try:
            client = genai.Client(api_key=key)
            
            # Cấu hình nạp System Instruction & nâng cao tư duy cho Model
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7 # Giúp câu trả lời sáng tạo và tự nhiên hơn
                )
            )
            return response.text
        except Exception as e:
            print(f"⚠️ Key số {idx+1} gặp lỗi: {e}. Đang chuyển sang Key tiếp theo...")
            last_exception = e
            
    raise last_exception


# --- 4. XỬ LÝ TIN NHẮN CHAT ---
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message) or message.content.startswith('!ask'):
        prompt = message.content.replace(f'<@{bot.user.id}>', '').replace('!ask', '').strip()

        if not prompt:
            await message.channel.send("Nhập câu hỏi nữa bro!")
            return

        # Lấy model user đã chọn, nếu chưa chọn thì lấy mặc định 3.6-flash
        current_model = user_models.get(message.author.id, "gemini-3.6-flash")

        async with message.channel.typing():
            try:
                response = gemini_client.models.generate_content(
                    model=current_model,
                    contents=prompt
                )

                reply = response.text

                if len(reply) > 2000:
                    for i in range(0, len(reply), 1900):
                        await message.reply(reply[i:i+1900])
                else:
                    await message.reply(reply)

            except Exception as e:
                await message.channel.send(f"Lỗi rồi bro ({current_model}): {e}")

    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
