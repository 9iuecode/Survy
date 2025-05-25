import discord
import asyncio
import traceback
from datetime import datetime
from discord.ext import commands
from discord import app_commands
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.common.action_chains import ActionChains  
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
# KONFIGURASI
token = 'MTM2NDU1OTQ2OTE5OTIzMzAyNA.GrNrhK.M9c_rw9dqPrS7_Ga9_-_HFsiR63vToYvCw8cqg'
CHANNEL_ID = [1364460757084930101]
GUILD_ID = 1095916483370029128
REDEEM_URL = 'https://wos-giftcode.centurygame.com/'

# BOT SETUP
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(
    command_prefix='?',
    intents=intents,
    executor=ThreadPoolExecutor(max_workers=4)
)

# SELENIUM FUNCTION
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920x1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])  # Ditambahkan
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.set_page_load_timeout(30)
    return driver

# REDEEM FUNCTION
async def redeem_code(driver, player_id: str, code: str, interaction: discord.Interaction):
    try:
        # interaction.followup.send [Function]
        async def send_msg(content: str, ephemeral: bool = False):
            await interaction.followup.send(content, ephemeral=ephemeral)

        # interaction.followup.send_file [Function]
        async def send_file(file_path: str):
            with open(file_path, 'rb') as f:
                await interaction.followup.send(file=discord.File(f))
        
        # update [Function]
        recent_message = await interaction.followup.send("🤖 Starting to redeem...")
        await asyncio.sleep(2)
        async def update(text=None):
            await recent_message.edit(content=text)
            await asyncio.sleep(0.3)

        # [1] Opening website page
        await update("🌐 Opening website page...")
        await bot.loop.run_in_executor(None, lambda: driver.get(REDEEM_URL))
        await asyncio.sleep(2)

        # [2] Player Id input
        await update("🔍 Processing player id...")
        try:
                # Waiting for page load
                await bot.loop.run_in_executor(
                    None,
                    lambda: WebDriverWait(driver, 30).until(
                        lambda d: d.execute_script('return document.readyState') == 'complete'
                    )
                )

                # Mouse simulation
                await bot.loop.run_in_executor(
                    None,
                    lambda: driver.execute_script("""
                        window.scrollTo(0, 200);
                        const mouseMoveEvent = new MouseEvent('mousemove', {
                            view: window,
                            bubbles: true,
                            cancelable: true,
                            clientX: 100,
                            clientY: 200
                        });
                        document.dispatchEvent(mouseMoveEvent);
                    """)
                )
                await asyncio.sleep(1)

                # Element selection
                id_field = None
                selectors = [
                    '//input[@data-v-781897ff]',
                    '//input[@placeholder="Player ID"]',
                    '//input[contains(@id,"player")]',
                    '//input[@type="text"][@maxlength="10"]'
                ]
                
                for selector in selectors:
                    try:
                        elements = await bot.loop.run_in_executor(
                            None,
                            lambda s=selector: driver.find_elements(By.XPATH, s)
                        )
                        
                        if elements:
                            # Highlight element dengan border merah
                            await bot.loop.run_in_executor(
                                None,
                                lambda e=elements[0]: driver.execute_script(
                                    "arguments[0].style.border='3px solid red';", e)
                            )
                            id_field = elements[0]
                            break
                            
                    except:
                        continue

                if not id_field:
                    await update(f"❗Element for player id is not found")
                    return

                # Clicking simulation
                await bot.loop.run_in_executor(
                    None,
                    lambda: driver.execute_script("""
                        arguments[0].click();
                        arguments[0].value = '';
                    """, id_field)
                )
                await asyncio.sleep(0.5)
                
                await bot.loop.run_in_executor(
                    None,
                    lambda: id_field.send_keys(player_id)
                )
                
                print (f"Id: {player_id} is available!")

        except Exception as e:
                await update (f"❌ id: {player_id} is invalid")

        # [3] Log-in
        try:
            await update("🔑 Processing to log-in...")
            
            # Waiting for page load
            await bot.loop.run_in_executor(
                None,
                lambda: WebDriverWait(driver, 30).until(
                    lambda d: d.execute_script("""
                        return document.readyState === 'complete' && 
                            document.body.scrollHeight > 0
                    """)
                )
            )

            # Mouse simulation
            await bot.loop.run_in_executor(
                None,
                lambda: driver.execute_script("""
                    window.scrollTo({
                        top: document.body.scrollHeight/3,
                        behavior: 'smooth'
                    });
                    const hoverEvent = new MouseEvent('mouseover', {
                        bubbles: true,
                        cancelable: true
                    });
                    arguments[0].dispatchEvent(hoverEvent);
                """, id_field) 
            )
            await asyncio.sleep(1.5)

            # 3. Element selection
            login_button = None
            login_selectors = [
                '//button[@data-v-781897ff]',
                '//button[@class="btn login_btn"]',
                '//button[contains(@class="btn login_btn")]',
                '//span[@data-v-781897ff]',
                '//span[contains(text(), "Login")]'
            ]

            for selector in login_selectors:
                try:
                    elements = await bot.loop.run_in_executor(
                        None,
                        lambda s=selector: driver.find_elements(By.XPATH, s)
                    )
                    if elements:
                        # Visual feedback
                        await bot.loop.run_in_executor(
                            None,
                            lambda e=elements[0]: driver.execute_script(
                                "arguments[0].style.boxShadow='0 0 10px lime';", e)
                        )
                        login_button = elements[0]
                        break
                except:
                    continue

            if not login_button:
                await update(f"❗Element for log-in is not found")
                return

            # Clicking simulation
            await bot.loop.run_in_executor(
                None,
                lambda: driver.execute_script("""
                    const btn = arguments[0];
                    btn.click();
                    setTimeout(() => {
                        btn.style.boxShadow = 'none';
                    }, 1000);
                """, login_button)
            )
            await asyncio.sleep(2)

            # Log-in Notifications
            await bot.loop.run_in_executor(
                None,
                lambda: WebDriverWait(driver, 20).until(
                    EC.invisibility_of_element_located((By.XPATH, '//input[@placeholder="Player ID"]'))
                )
            )
            print ("Log-in sucessful!")

        except Exception as e:
            await bot.loop.run_in_executor(
                None,
                lambda: driver.save_screenshot('login_failed.png')
            )
            await update (f"❌ Failed to log-in")
            return

        # [4] Gift code input
        try:
            await update("🎁 Processing gift code...")
            
            # Waiting to page load
            await bot.loop.run_in_executor(
                None,
                lambda: WebDriverWait(driver, 30).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
            )

            # Mouse simulation
            await bot.loop.run_in_executor(
                None,
                lambda: driver.execute_script("""
                    window.scrollTo(0, 300);
                    const mouseMoveEvent = new MouseEvent('mousemove', {
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        clientX: 150,
                        clientY: 300
                    });
                    document.dispatchEvent(mouseMoveEvent);
                """)
            )
            await asyncio.sleep(1)

            # Element selection
            code_field = None
            selectors = [
                '//input[@data-v-781897ff]',   
                '//input[@class="input_wrap"]',           
                '//input[@placeholder="Enter Gift Code"]',                   
                '//input[@type="text"][@maxlength="20"]'       
            ]
            
            for selector in selectors:
                try:
                    elements = await bot.loop.run_in_executor(
                        None,
                        lambda s=selector: driver.find_elements(By.XPATH, s)
                    )
                    
                    if elements:
                        # Visual feedback
                        await bot.loop.run_in_executor(
                            None,
                            lambda e=elements[0]: driver.execute_script(
                                "arguments[0].style.border='3px solid green';", e)
                        )
                        code_field = elements[0]
                        break
                        
                except:
                    continue

            if not code_field:
                await update("❗Element for gift code is not found")
                return

            # Clicking simulation
            await bot.loop.run_in_executor(
                None,
                lambda: driver.execute_script("""
                    arguments[0].click();
                    arguments[0].value = '';
                """, code_field)
            )
            await asyncio.sleep(0.5)
            
            await bot.loop.run_in_executor(
                None,
                lambda: code_field.send_keys(code)
            )
            
            print (f"Successfully input: {code} as a gift code!")

        except Exception as e:
            await update(f"❌ Invalid gift code")
            return
        
        # [6] Captcha Solver
        await update("🛡️ Processing CAPTCHA...")
        try:
            # Element Selection
            captcha_element = None
            captcha_selectors = [
            '//img[contains(@src, "data:image") and contains(@class, "verify")]',
            '//img[contains(@src, "jpeg;base64")]',
            '//div[contains(@class, "captcha")]//img',
            '//img[@alt="captcha"]',
            '//div[@data-v-781897ff]//img'
            ]

            for selector in captcha_selectors:
                try:
                    elements = await bot.loop.run_in_executor(
                    None,
                    lambda s=selector: driver.find_elements(By.XPATH, s)
                    )
                    if elements:
                        captcha_element = elements[0]
                        await bot.loop.run_in_executor(
                        None,
                        lambda e=elements[0]: driver.execute_script(
                            "arguments[0].style.border='3px solid yellow';", e)
                    )
                    break
                except:
                    continue

            if not captcha_element:
                await update("❌Element for CAPTCHA is not found")
                return
            
            # Captcha Picture
            captcha_file = 'captcha.png'
            await bot.loop.run_in_executor(
            None,
            lambda: captcha_element.screenshot(captcha_file)
            )
            await send_file(captcha_file)

            # Manual input
            def check(m):
                 return m.author == interaction.user and m.channel == interaction.channel
            await update(f"⌛Waiting for 60s, please do input the code correctly")
            
            try:
                # Waiting for CAPTCHA for 60s
                msg = await bot.wait_for('message', timeout=60.0, check=check)
                final_text = msg.content.strip()[:4]
                
                if len(final_text) != 4 or not final_text.isalnum():
                    await send_msg("⚠️ Captcha format is invalid! Please input 4 numerics characters.")
                    return False
                    
                print (f"CAPTCHA: {final_text} inputted")

            except asyncio.TimeoutError:
                await interaction.followup.send(f"⏰ Input Timeout!")
                return

            # 4. Input hasil ke form
            await update(f"📨 Confirming CAPTCHA...")
            
            input_field = await bot.loop.run_in_executor(
                None,
                lambda: WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//input[contains(@placeholder, "Enter verification code")]')
                    )
                )
            )

            await asyncio.sleep(0.5)
            
            await bot.loop.run_in_executor(
                None,
                lambda: input_field.send_keys(final_text)
            )
            await asyncio.sleep(0.5)

        except Exception as e:
            await update (f"❌ Invalid CAPTCHA")
            return

        # Confirm Button
        try:
            await update("📮 Processing to confirm...")
            
            # Element selection
            confirm_selectors = [
                '//*[contains(@class, "btn exchange_btn") and contains(text(), "Confirm")]',
                '//div[contains(@class, "btn exchange_btn") and contains(text(), "Confirm")]'
            ]
            
            confirm_button = None

            for selector in confirm_selectors:
                try:
                    elements = await bot.loop.run_in_executor(
                        None,
                        lambda s=selector: WebDriverWait(driver, 5).until(
                            EC.presence_of_all_elements_located((By.XPATH, s))
                        )
                    )
                    
                    if elements:
                        # Debugging
                        await bot.loop.run_in_executor(
                            None,
                            lambda e=elements[0]: e.get_attribute('outerHTML')
                        )
                        confirm_button = elements[0]
                        break
                        
                except Exception as e:
                    await update (f"❗Element for confirm is not found!")
                    continue

            if not confirm_button:
                # Debugging
                await bot.loop.run_in_executor(None, lambda: driver.save_screenshot('confirm_error.png'))
                page_html = await bot.loop.run_in_executor(None, lambda: driver.page_source)
                with open('page_source.html', 'w', encoding='utf-8') as f:
                    f.write(page_html)
                    
                error_msg = await update("❌ Tombol Confirm tidak ditemukan dengan semua selector")
                return error_msg
            
            # Mouse simulation
            await bot.loop.run_in_executor(
                None,
                lambda: driver.execute_script("""
                    arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});
                    arguments[0].style.border = '3px solid lime';
                """, confirm_button)
            )
            await asyncio.sleep(1)

            # 2nd Debugging 
            is_enabled = await bot.loop.run_in_executor(
                None,
                lambda: confirm_button.is_enabled()
            )
            is_displayed = await bot.loop.run_in_executor(
                None,
                lambda: confirm_button.is_displayed()
            )
            
            if not is_enabled or not is_displayed:
                return f"❌ Button is unavailabe to click! (Enabled: {is_enabled}, Displayed: {is_displayed})"
            # Another click options
            try:
                # Metode 1: Klik dengan JavaScript langsung
                await bot.loop.run_in_executor(
                    None,
                    lambda: driver.execute_script("arguments[0].click();", confirm_button)
                )
                await asyncio.sleep(2)
                
                # Make sure bot is clicking
                try:
                    await bot.loop.run_in_executor(
                        None,
                        lambda: WebDriverWait(driver, 5).until(
                            EC.staleness_of(confirm_button)
                        )
                    )
                    print ("Confirm button pressed!")
                except:
                    # Another method
                    actions = ActionChains(driver)
                    await bot.loop.run_in_executor(
                        None,
                        lambda: actions.move_to_element(confirm_button).click().perform()
                    )
                    await asyncio.sleep(0.5)
                    
            except Exception as click_error:
                await update (f"❌ Failed to click: {str(click_error)}\n" 
                              f"📌 Button status: Enabled={is_enabled}, Displayed={is_displayed}")
                return

        except Exception as e:
            error_trace = traceback.format_exc()
            await update(f"❌ System error: {str(e)}\n🔧 Traceback:\n{error_trace}")

        # [8] Message Output 
        try:
            await update("🪄 Processing redeem result...")
    
            # Waiting for page load
            await bot.loop.run_in_executor(
                None,
                lambda: WebDriverWait(driver, 30).until(
                    lambda d: d.execute_script("""
                        return document.readyState === 'complete' && 
                            document.body.scrollHeight > 0
                    """)
                )
            )

            # Element selection
            result_element = None
            result_selectors = [
                # Redeemed Status
                '//p[contains(text(), "Redeemed, please claim the rewards in your mail!")]',
                # Already Claimed Status
                '//p[contains(text(), "Already claimed, unable to claim again.")]',
                # Relog-in Status
                '//p[contains(text(), "Please log in to relevant character before redemption.")]',
                # Incorrect Captcha Status
                '//p[contains(text(), "Incorrect code, please retry the verification.")]',
                # Captcha Expired Status
                '//p[contains(text(), "Code expired, please retry the verification.")]',
                # Gift-Code not Found
                '//p[contains(text(), "Gift Code not found, this is case-sensitive!")]',
                # Gift-Code Expired
                '//p[contains(text(), "Expired, unable to claim.")]'

            ]

            for selector in result_selectors:
                try:
                     elements = await bot.loop.run_in_executor(
                None,
                lambda s=selector: WebDriverWait(driver, 5).until(
                    EC.visibility_of_all_elements_located((By.XPATH, s))
                    )
                    )
                     if elements:
                         # Visual debugging highlight
                        await bot.loop.run_in_executor(
                            None,
                            lambda e=elements[0]: driver.execute_script(
                                "arguments[0].style.border='2px solid purple';"
                                "arguments[0].style.boxShadow='0 0 10px purple';", e)
                        )
                        result_element = elements[0]
                        # Debugging
                        """await interaction.followup.send(f"✅ Hasil ditemukan dengan selector: `{selector}`")"""
                        break
                     
                except:
                    continue

            if not result_element:
                await update("❗Element for result is not found")
                return

            # Debugging 
            """
            await bot.loop.run_in_executor(
                None,
                lambda: driver.save_screenshot('result_output.png')
            )
            await send_file('result_output.png')"""

            # 4. Get complete message text
            message_text = await bot.loop.run_in_executor(
                None,
                lambda: result_element.get_attribute('textContent').strip()
            )

            # 5. Status Selection
            status_map = {
                'Redeemed': '**Successful**: Gift code redeemed.',
                'Code expired': '**Error**: Captcha code expired.',
                'Incorrect': '**Error**: Captcha code incorrect.',
                'Please': '**Warning**: Please relog-in with correct character!',
                'already': '**Error**: Code was already claimed.',
                'not found': '**Error**: Gift code was not found.',
                'Expired': '**Error**: Gift code expired, unable to claim.'

            }

            detected_status = "⚠️ Unknown status"
            for keyword, status in status_map.items():
                if keyword.lower() in message_text.lower():
                    detected_status = status
                    break

            # Player Profile 
            player_name = driver.find_element(By.XPATH, '//p[contains(@class, "name")]').text
            state_info = driver.find_element(By.XPATH, '//p[contains(@class, "other") and contains(text(), "State:")]').text

            # Avatar Image
            avatar_img = driver.find_element(By.XPATH, '//div[contains(@class, "roleInfo_con") and .//img]')
            a_img = avatar_img.find_element(By.XPATH, './/img[contains(@class, "img avatar")]').get_attribute("src")

            # Furnace Info [ PENDING ]
            """player_level = driver.find_element(By.XPATH, '//p[contains(@class, "other") and contains(text(), "Furnace Level:")]')
            p_img = player_level.find_element(By.XPATH, './/img').get_attribute("src")   """

            # Embedded Message Output
            embed = discord.Embed(
                colour=discord.Colour.gold(),
                title="DETAILS",
                description=("🗃️ Rewards will be directly sent to Character's mail after redemption. If it fails, try again with correct values ✅"
                )
            )

            # Author Field
            embed.set_author(
                name="Survy REDEEM",
                icon_url="https://i.imgur.com/XKb9U3D.jpeg"
            )

            # Player Profile Field
            embed.add_field(
                name="🥸 Profile 🤓",
                value=f"Name: {player_name}\n"
                      f"ID: {player_id}\n"
                      f"{state_info}",
                inline=False
            )
            
            # Status Field
            embed.add_field(
                name="📊 Status 📊",
                value=f"{detected_status}\n"
                      f"Gift Code: **{code}**", 
                inline=False
            )

            # Avatar Image Field
            embed.set_thumbnail(url=a_img)

            # Footer Field
            hari = datetime.now().strftime("%d/%m/%Y")
            jam = datetime.now().strftime("%H:%M:%S")
            embed.set_footer(
                text=f"Date: {hari}\n"
                     f"Time: {jam}\n"
                     f"💖 Thank you for using Survy, have a great day! 💖"
            )
            await update(f"🎉 Here's your redeem result!")
            await interaction.followup.send(embed=embed)
        
        except TimeoutException:
            return "⌛ Timeout: Tidak menerima respon hasil redeem"
        
        except Exception as e:
            return f"⚠️ Error Sistem: {str(e)}"
        
        print(f"{player_id}: Done")

    except Exception as e:
        await bot.loop.run_in_executor(
            None,
            lambda: driver.save_screenshot('fatal_error.png')
        )
        return f"💀 Fatal Error: {str(e)}"

# SLASH COMMANDS
@bot.tree.command(
    name="redeem",
    description="Redeem kode hadiah Whiteout Survival",
    guild=discord.Object(id=GUILD_ID))

@app_commands.describe(
    player_id="ID Pemain kamu",
    code="Kode redeem hadiah"
)
async def slash_redeem(interaction: discord.Interaction, player_id: str, code: str):
    if interaction.channel.id not in CHANNEL_ID:
        await interaction.response.send_message(
            "❌ Perintah hanya bisa digunakan di channel khusus!",
            ephemeral=True
        )
        return

    await interaction.response.defer(thinking=True) 
    driver = setup_driver()
    
    try:
        result = await redeem_code(driver, player_id, code, interaction)
        await interaction.followup.send(result)
    except Exception as e:
        return
    finally:
        await bot.loop.run_in_executor(None, driver.quit)
# Discord Commands
@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} siap digunakan!')
    try:
        # Sync command ke guild tertentu
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print(f" Slash commands tersinkronisasi untuk guild {GUILD_ID}")
    except Exception as e:
        print(f"❌ Gagal sync commands: {e}")

if __name__ == '__main__':
    bot.run(token)