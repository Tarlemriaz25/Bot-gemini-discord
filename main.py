import os
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from discord.ext import commands
from google import genai

# --- 1. SERVER GIẢ CHO RENDER ---
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

# --- 2. QUẢN LÝ DỮ LIỆU XU (LƯU VÀO FILE JSON) ---
COINS_FILE = "coins.json"
DEFAULT_COINS = 5  # Số xu tặng cho người mới lần đầu dùng bot

def load_coins():
    if os.path.exists(COINS_FILE):
        try:
            with open(COINS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_coins(data):
    with open(COINS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_user_coins(user_id):
    coins_data = load_coins()
    str_id = str(user_id)
    if str_id not in coins_data:
        coins_data[str_id] = DEFAULT_COINS
        save_coins(coins_data)
    return coins_data[str_id]

def use_user_coin(user_id):
    coins_data = load_coins()
    str_id = str(user_id)
    current = coins_data.get(str_id, DEFAULT_COINS)
    if current > 0:
        coins_data[str_id] = current - 1
        save_coins(coins_data)
        return True, coins_data[str_id]
    return False, 0

def add_user_coins(user_id, amount):
    coins_data = load_coins()
    str_id = str(user_id)
    current = coins_data.get(str_id, DEFAULT_COINS)
    coins_data[str_id] = current + amount
    save_coins(coins_data)
    return coins_data[str_id]

# --- 3. KHỞI TẠO BOT & API KEYS ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

API_KEYS = []
key1 = os.getenv("GEMINI_API_KEY_1")
key2 = os.getenv("GEMINI_API_KEY_2")

if key1: API_KEYS.append(key1.strip())
if key2: API_KEYS.append(key2.strip())
if not API_KEYS:
    old_key = os.getenv("GEMINI_API_KEY")
    if old_key: API_KEYS.append(old_key.strip())

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

user_models = {}

# --- 4. HÀM GỌI GEMINI API ---
def generate_content_with_fallback(prompt, model_name):
    last_exception = None
    system_instruction = (
        "Bạn là một trợ lý AI cá nhân thông minh, am hiểu sâu sắc về công nghệ, phần cứng, lập trình, "
        "và hệ thống Android/Linux. Hãy luôn suy luận cẩn thận, chi tiết, cung cấp giải pháp chính xác "
        "và hữu ích nhất. Trả lời bằng tiếng Việt thân thiện, tự nhiên, trình bày đẹp mắt bằng Markdown."
    )
    
    for idx, key in enumerate(API_KEYS):
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7
                )
            )
            return response.text
        except Exception as e:
            print(f"⚠️ Key số {idx+1} gặp lỗi: {e}. Đang chuyển sang Key tiếp theo...")
            last_exception = e
            
    raise last_exception

# --- 5. SỰ KIỆN BOT ONLINE ---
@bot.event
async def on_ready():
    custom_status = discord.CustomActivity(name="Chat với tớ bằng !ask nhé ✨")
    await bot.change_presence(activity=custom_status)
    try:
        synced = await bot.tree.sync()
        print(f"✅ Đã sync {len(synced)} lệnh slash command!")
    except Exception as e:
        print(f"⚠️ Lỗi sync command: {e}")
    print(f"🚀 Bot đã online với tên: {bot.user}")

# --- 6. SLASH COMMANDS (XU & MODEL) ---
@bot.tree.command(name="coins", description="Kiểm tra số xu còn lại của bro")
async def check_coins(interaction: discord.Interaction):
    coins = get_user_coins(interaction.user.id)
    await interaction.response.send_message(
        f"🪙 Bro **{interaction.user.name}** hiện đang có: **{coins} xu**.",
        ephemeral=True
    )

@bot.tree.command(name="daily", description="Điểm danh nhận xu mỗi ngày (Tặng 3 xu)")
async def daily_coins(interaction: discord.Interaction):
    # Cộng thêm 3 xu
    new_total = add_user_coins(interaction.user.id, 3)
    await interaction.response.send_message(
        f"🎉 Bro đã nhận được 3 xu điểm danh! Tổng số xu hiện tại: **{new_total} xu**.",
        ephemeral=True
    )

@bot.tree.command(name="model", description="Chọn model Gemini bro muốn dùng")
@app_commands.choices(selected_model=[
    app_commands.Choice(name="Gemini 2.0 Flash (Nhanh & Chuẩn - Mặc định)", value="gemini-2.0-flash"),
    app_commands.Choice(name="Gemini 1.5 Flash (Ổn định)", value="gemini-1.5-flash"),
    app_commands.Choice(name="Gemini 1.5 Pro (Thông minh hơn)", value="gemini-1.5-pro"),
])
async def set_model(interaction: discord.Interaction, selected_model: app_commands.Choice[str]):
    user_models[interaction.user.id] = selected_model.value
    await interaction.response.send_message(
        f"✅ Đã đổi model cho bro **{interaction.user.name}** thành: `{selected_model.value}`!",
        ephemeral=True
    )

# --- 7. XỬ LÝ TIN NHẮN (KIỂM TRÁ VÀ TRỪ XU) ---
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message) or message.content.startswith('!ask'):
        prompt = message.content.replace(f'<@{bot.user.id}>', '').replace('!ask', '').strip()

        if not prompt:
            await message.channel.send("Nhập câu hỏi nữa bro!")
            return

        # KIỂM TRÃ VÀ TRỪ XU
        success, remaining_coins = use_user_coin(message.author.id)
        if not success:
            await message.reply(
                "❌ **Bro đã hết xu mất rồi!**\n"
                "Dùng lệnh `/daily` để nhận xu miễn phí mỗi ngày hoặc nhờ admin cộng thêm nhé!"
            )
            return

        current_model = user_models.get(message.author.id, "gemini-2.0-flash")

        async with message.channel.typing():
            try:
                reply = generate_content_with_fallback(prompt, current_model)
                
                # Báo số xu còn lại ở cuối
                reply_text = f"{reply}\n\n*(🪙 Còn lại: {remaining_coins} xu)*"

                if len(reply_text) > 2000:
                    for i in range(0, len(reply_text), 1900):
                        await message.reply(reply_text[i:i+1900])
                else:
                    await message.reply(reply_text)

            except Exception as e:
                # Nếu API bị lỗi thì hoàn lại 1 xu cho user
                add_user_coins(message.author.id, 1)
                await message.channel.send(f"❌ Lỗi API nên đã hoàn lại 1 xu cho bro: {e}")

    await bot.process_commands(message)

# --- 8. CHẠY BOT ---
bot.run(DISCORD_TOKEN)
