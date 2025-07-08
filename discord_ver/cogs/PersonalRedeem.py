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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
                
class PersonalRedeem(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.CHANNEL_ID = [1364460757084930101]
        self.OSBC = 1095916483370029128
        self.REDEEM_URL = 'https://wos-giftcode.centurygame.com/'

    def setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--window-size=1920x1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])  
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        driver.set_page_load_timeout(30)
        return driver
    
    class RedeemOptions(discord.ui.Select):
        def __init__(self, player_id: str, code: str = None):
            self.player_id = player_id
            self.code = code

            options = [
                discord.SelectOption(
                    label="Re-redeem in current ID",
                    description=f"Current ID: {player_id}",
                    value="current_id"
                ),
                discord.SelectOption(
                    label="Re-redeem with new ID",
                    description=f"Input new ID",
                    value="new_id"
                )
            ]

            super().__init__(
                placeholder="Choose re-redeem option...",
                min_values=1,
                max_values=1,
                options=options

            )

        async def callback(self, interaction: discord.Interaction):
            if self.values[0] == "current_id":
                modal = discord.ui.Modal(title=f"Re-redeem for {self.player_id}")
                modal.add_item(
                    discord.ui.TextInput(
                        label="Re-input gift code",
                        placeholder="Input gift code",
                        required=True,
                        max_length=20
                    )
                )

                async def on_submit(interaction: discord.Interaction):
                    new_gcode = modal.children[0].value
                    await self.view.redeem_with_current_id(interaction, new_gcode)
                
                modal.on_submit = on_submit
                await interaction.response.send_modal(modal)

            elif self.values[0] == "new_id":
                modal = discord.ui.Modal(title="Re-redeem for new id")
                modal.add_item(
                    discord.ui.TextInput(
                        label="New player ID",
                        placeholder="Input new player ID",
                        required=True,
                        max_length=10
                    )
                )

                modal.add_item(
                    discord.ui.TextInput(
                        label="Gift Code",
                        placeholder="Input gift code",
                        required=True,
                        max_length=20
                    )
                )

                async def on_submit(interaction: discord.Interaction):
                    new_id = modal.children[0].value
                    new_gcode = modal.children[1].value
                    await self.view.redeem_with_new_id(interaction, new_id, new_gcode)
                
                modal.on_submit = on_submit
                await interaction.response.send_modal(modal)
    
    class RedeemView(discord.ui.View):
        def __init__(self, cog, player_id: str, code: str = None):
            super().__init__(timeout=180)
            self.cog = cog
            self.player_id = player_id
            self.code = code

        @discord.ui.button(
            label="Re-redeem",
            style=discord.ButtonStyle.blurple,
            emoji="🔃"
        )

        async def re_redeem_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            dropdown = self.cog.RedeemOptions(self.player_id, self.code)
            view = discord.ui.View(timeout=120)
            view.add_item(dropdown)
            view.redeem_with_current_id = self.redeem_with_current_id
            view.redeem_with_new_id = self.redeem_with_new_id

            await interaction.response.send_message(
                "Choose redeem options: ",
                view=view,
                ephemeral=False
            )

        async def redeem_with_current_id(self, interaction: discord.Interaction, code: str):
            await interaction.response.defer(thinking=True)
            await interaction.followup.send("RE-REDEEM BEGIN!")
            driver = self.cog.setup_driver()
            
            try:
                await self._click_confirm_after(driver, interaction)
                await interaction.channel.send("🔃 |`Starting to re-redeem`\n🍳 |`Let's cook again!`")
                if not await self.cog._open_website(driver):
                    return

                if not await self.cog._input_player_id(driver, self.player_id):
                    return

                if not await self.cog._login(driver):
                    return

                if not await self.cog._input_gift_code(driver, code):
                    return

                captcha_result = await self.cog._restart_captcha(driver, interaction)
                if not captcha_result:
                    return

                if not await self.cog._confirm_redemption(driver):
                    return

                await interaction.channel.send("🎉 |`Here's your redeem result!`")
                await self.cog._get_redemption_result(driver, self.player_id, code, interaction)

            except Exception as e:
                await interaction.followup.send(f"💀 Fatal Error: {str(e)}")
            finally:
                await self.cog.bot.loop.run_in_executor(None, driver.quit)
            
        async def redeem_with_new_id(self, interaction: discord.Interaction, new_id, code: str):
            await interaction.response.defer(thinking=True)
            await interaction.followup.send("RE-REDEEM BEGIN!")
            driver = self.cog.setup_driver()

            try:
                await self._click_confirm_after(driver, interaction)
                await interaction.channel.send("🔃 |`Starting to re-redeem`\n🍳 |`Let's cook again!`")
                if not await self.cog._open_website(driver,):
                    return
                
                if not await self._retreat_for_new_id(driver, interaction, new_id):
                    return

                if not await self.cog._login(driver):
                    return

                if not await self.cog._input_gift_code(driver, code):
                    return

                captcha_result = await self.cog._solve_captcha(driver, interaction)
                if not captcha_result:
                    return

                if not await self.cog._confirm_redemption(driver):
                    return
                await interaction.channel.send("🎉 |`Here's your redeem result!`")
                await self.cog._get_redemption_result(driver, self.player_id, code, interaction)

            except Exception as e:
                await interaction.followup.send(f"💀 Fatal Error: {str(e)}")
            finally:
                await self.cog.bot.loop.run_in_executor(None, driver.quit)

        async def _click_confirm_after(self, driver, interaction):
            try:
                confirm_after = await self.cog._find_element(driver, [
                    '//*[contains(@class, "confirm_btn") and contains(text(), "Confirm")]',
                    '//div[contains(@class, "confirm_btn") and contains(text(), "Confirm")]'
                ],  'orange')

                if confirm_after:
                    await interaction.followup.send("Clicking confirm button after redemption...", ephemeral=True)
                    await self.cog.bot.loop.run_in_executor(
                        None,
                        lambda: driver.execute_script("arguments[0].click();", confirm_after)
                    )
                    await asyncio.sleep(0.5)
                    return True
            except Exception as e:
                print(f"Click Error: {e}")
                return False
        
        async def _retreat_for_new_id(self, driver, interaction, new_id):
            try:
                exit_button = await self.cog._find_element(driver, [
                    '//*[contains(@class, "exit_con")]',
                    '//div[contains(@class, "exit_con")]',
                    '//*[contains(@class, "exit_icon")]',
                    '//div[contains(@class, "exit_icon")]',
                    '//p[contains(@class, "exit_text") and contains(text(), "Retreat")]'
                ],  'red')
                
                if exit_button:
                    await self.cog.bot.loop.run_in_executor(
                        None,
                        lambda: driver.execute_script("arguments[0].click()", exit_button)
                    )
                    await asyncio.sleep(1)
                
                id_field = await self.cog._find_element(driver, [
                    '//input[contains(@type, "text") and contains(@placeholder, "Player ID")]'
                ],  'blue')
                if not id_field:
                    await interaction.followup.send("❌ ID input field not found", ephemeral=True)
                    return False
                
                await self.cog.bot.loop.run_in_executor(
                    None,
                    lambda: driver.execute_script("""
                        arguments[0].focus();
                        arguments[0].value = '';
                        arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                        arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                    """, id_field)
                )
                await self.cog._input_text(driver, id_field, new_id)
                await asyncio.sleep(0.5)

                return True
            except Exception as e:
                print(f"Click Error: {e}")
                return False

    
    async def _send_msg(self, interaction, content: str, ephemeral: bool = False):
        await interaction.followup.send(content, ephemeral=ephemeral)

    async def _send_file(self, interaction, file_path: str):
        with open(file_path, 'rb') as f:
            await interaction.followup.send(file=discord.File(f))

    async def _wait_for_page_load(self, driver):
        await self.bot.loop.run_in_executor(
            None,
            lambda: WebDriverWait(driver, 30).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
        )

    async def _simulate_mouse_movement(self, driver, x=150, y=300):
        await self.bot.loop.run_in_executor(
            None,
            lambda: driver.execute_script(f"""
                window.scrollTo(0, {y});
                const mouseMoveEvent = new MouseEvent('mousemove', {{
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: {x},
                    clientY: {y}
                }});
                document.dispatchEvent(mouseMoveEvent);
            """)
        )
        await asyncio.sleep(1)

    async def _find_element(self, driver, selectors, highlight_color='red'):
        for selector in selectors:
            try:
                elements = await self.bot.loop.run_in_executor(
                    None,
                    lambda s=selector: driver.find_elements(By.XPATH, s)
                )
                
                if elements:
                    await self.bot.loop.run_in_executor(
                        None,
                        lambda e=elements[0]: driver.execute_script(
                            f"arguments[0].style.border='3px solid {highlight_color}';", e)
                    )
                    return elements[0]
            except:
                continue
        return None

    async def _input_text(self, driver, element, text):
        await self.bot.loop.run_in_executor(
            None,
            lambda: driver.execute_script("""
                arguments[0].click();
                arguments[0].value = '';
            """, element)
        )
        await asyncio.sleep(0.5)
        await self.bot.loop.run_in_executor(
            None,
            lambda: element.send_keys(text)
        )

    async def _open_website(self, driver):
        try:
            await self.bot.loop.run_in_executor(None, lambda: driver.get(self.REDEEM_URL))
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            print (f"Failed to load web page\nError: {str(e)}")
            return False

    async def _input_player_id(self, driver, player_id):
        try:
            await self._wait_for_page_load(driver)
            await self._simulate_mouse_movement(driver, 100, 200)

            id_field = await self._find_element(driver, [
                '//input[@data-v-781897ff]',
                '//input[@placeholder="Player ID"]',
                '//input[contains(@id,"player")]',
                '//input[@type="text"][@maxlength="10"]'
            ], 'red')

            if not id_field:
                print("Element for player id is not found")
                return False

            await self._input_text(driver, id_field, player_id)
            print(f"Id: {player_id} is available!")
            
            # Custom scroll and hover
            await self.bot.loop.run_in_executor(
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
            await asyncio.sleep(0.5)
            return True
        
        except Exception as e:
            print(f"id: {player_id} is invalid\nError: ({str(e)})")
            return False

    async def _login(self, driver):
        try:
            await self._wait_for_page_load(driver)

            login_button = await self._find_element(driver, [
                '//button[@data-v-781897ff]',
                '//button[@class="btn login_btn"]',
                '//button[contains(@class,"btn login_btn")]',
                '//span[@data-v-781897ff]',
                '//span[contains(text(), "Login")]'
            ], 'lime')

            if not login_button:
                await print("Element for log-in is not found")
                return False

            await self.bot.loop.run_in_executor(
                None,
                lambda: driver.execute_script("""
                    const btn = arguments[0];
                    btn.click();
                    setTimeout(() => {
                        btn.style.boxShadow = 'none';
                    }, 1000);
                """, login_button)
            )
            await asyncio.sleep(0.5)

            await self.bot.loop.run_in_executor(
                None,
                lambda: WebDriverWait(driver, 20).until(
                    EC.invisibility_of_element_located((By.XPATH, '//input[@placeholder="Player ID"]'))
                )
            )
            print("Log-in successful!")
            return True
        except Exception as e:
            await self.bot.loop.run_in_executor(
                None,
                lambda: driver.save_screenshot('login_failed.png')
            )
            print("Failed to log-in")
            return False

    async def _input_gift_code(self, driver, code):
        try:
            await self._wait_for_page_load(driver)
            await self._simulate_mouse_movement(driver)

            code_field = await self._find_element(driver, [
                '//input[@data-v-781897ff]',
                '//input[@class="input_wrap"]',
                '//input[@placeholder="Enter Gift Code"]',
                '//input[@type="text"][@maxlength="20"]'
            ], 'green')

            if not code_field:
                print("Element for gift code is not found")
                return False

            await self._input_text(driver, code_field, code)
            print(f"Successfully input: {code} as a gift code!")
            return True
        except Exception as e:
            print(f"Invalid gift code: {str(e)}")
            return False

    async def _solve_captcha(self, driver, interaction):
        try:
            captcha_element = await self._find_element(driver, [
                '//img[contains(@src, "data:image") and contains(@class, "verify")]',
                '//img[contains(@src, "jpeg;base64")]',
                '//div[contains(@class, "captcha")]//img',
                '//img[@alt="captcha"]',
                '//div[@data-v-781897ff]//img'
            ], 'yellow')

            if not captcha_element:
                print("Element for CAPTCHA is not found")
                return None

            captcha_file = 'captcha.png'
            await self.bot.loop.run_in_executor(
                None,
                lambda: captcha_element.screenshot(captcha_file)
            )
            mention = interaction.user.mention
            await interaction.channel.send(f"👤 |{mention}`Here's your CAPTCHA`\n⏳ |`Please input the code correctly within [60s]`")
            await interaction.channel.send(file=discord.File(captcha_file))
            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel
            
            try:
                msg = await self.bot.wait_for('message', timeout=60.0, check=check)
                final_text = msg.content.strip()[:4]
                
                if len(final_text) != 4 or not final_text.isalnum():
                    await self._send_msg(interaction, "⚠️ Captcha format is invalid! Please input 4 numerics characters.")
                    return None
                    
                print(f"CAPTCHA: {final_text} inputted")

                input_field = await self.bot.loop.run_in_executor(
                    None,
                    lambda: WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, '//input[contains(@placeholder, "Enter verification code")]')
                        )
                    )
                )

                await asyncio.sleep(0.5)
                await self._input_text(driver, input_field, final_text)
                return final_text

            except asyncio.TimeoutError:
                await interaction.followup.send("⏰ Input Timeout!")
                return None

        except Exception as e:
            print(f"Invalid CAPTCHA: {str(e)}")
            return None

    async def _confirm_redemption(self, driver):
        try:
            confirm_button = await self._find_element(driver, [
                '//*[contains(@class, "btn exchange_btn") and contains(text(), "Confirm")]',
                '//div[contains(@class, "btn exchange_btn") and contains(text(), "Confirm")]'
            ], 'lime')

            if not confirm_button:
                await self.bot.loop.run_in_executor(None, lambda: driver.save_screenshot('confirm_error.png'))
                page_html = await self.bot.loop.run_in_executor(None, lambda: driver.page_source)
                with open('page_source.html', 'w', encoding='utf-8') as f:
                    f.write(page_html)
                print("Confirm button not found in any selector")
                return False

            is_enabled = await self.bot.loop.run_in_executor(None, lambda: confirm_button.is_enabled())
            is_displayed = await self.bot.loop.run_in_executor(None, lambda: confirm_button.is_displayed())
            
            if not is_enabled or not is_displayed:
                print(f"Button is unavailable to click! (Enabled: {is_enabled}, Displayed: {is_displayed})")
                return False

            try:
                await self.bot.loop.run_in_executor(None, lambda: driver.execute_script("arguments[0].click();", confirm_button))
                await asyncio.sleep(0.5)
                
                try:
                    await self.bot.loop.run_in_executor(
                        None,
                        lambda: WebDriverWait(driver, 5).until(EC.staleness_of(confirm_button))
                    )
                    print("Confirm button pressed!")
                    return True
                except:
                    actions = ActionChains(driver)
                    await self.bot.loop.run_in_executor(
                        None,
                        lambda: actions.move_to_element(confirm_button).click().perform()
                    )
                    await asyncio.sleep(0.5)
                    return True
                    
            except Exception as click_error:
                print(f"Failed to click: {str(click_error)}")
                return False

        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"System error: {str(e)}\n🔧 Traceback:\n{error_trace}")
            return False

    async def _get_redemption_result(self, driver, player_id, code, interaction):
        try:
            await self._wait_for_page_load(driver)

            result_element = await self._find_element(driver, [
                '//p[contains(text(), "Redeemed, please claim the rewards in your mail!")]',
                '//p[contains(text(), "Already claimed, unable to claim again.")]',
                '//p[contains(text(), "Please log in to relevant character before redemption.")]',
                '//p[contains(text(), "Incorrect code, please retry the verification.")]',
                '//p[contains(text(), "Code expired, please retry the verification.")]',
                '//p[contains(text(), "Gift Code not found, this is case-sensitive!")]',
                '//p[contains(text(), "Expired, unable to claim.")]',
                '//p[contains(text(), "Claim limit reached, unable to claim.")]'
            ], 'purple')

            if not result_element:
                print("Element for result is not found")
                return None

            message_text = await self.bot.loop.run_in_executor(
                None,
                lambda: result_element.get_attribute('textContent').strip()
            )

            status_map = {
                'Redeemed': '**Successful**: Gift code redeemed.',
                'Code expired': '**Error**: Captcha code expired.',
                'Incorrect': '**Error**: Captcha code incorrect.',
                'Please': '**Warning**: Please relog-in with correct character!',
                'already': '**Error**: Code was already claimed.',
                'not found': '**Error**: Gift code was not found.',
                'Expired': '**Error**: Gift code expired, unable to claim.',
                'Claim': '**Error**: Claim limit reached.'
            }

            detected_status = "⚠️ Unknown status"
            for keyword, status in status_map.items():
                if keyword.lower() in message_text.lower():
                    detected_status = status
                    break

            player_name = driver.find_element(By.XPATH, '//p[contains(@class, "name")]').text
            state_info = driver.find_element(By.XPATH, '//p[contains(@class, "other") and contains(text(), "State:")]').text
            avatar_img = driver.find_element(By.XPATH, '//div[contains(@class, "roleInfo_con") and .//img]')
            a_img = avatar_img.find_element(By.XPATH, './/img[contains(@class, "img avatar")]').get_attribute("src")

            embed = discord.Embed(
                colour=discord.Colour.gold(),
                title="DETAILS",
                description="🗃️ Rewards will be directly sent to Character's mail after redemption. If it fails, try again with correct values ✅"
            )
            embed.set_author(name="Survy REDEEM", icon_url="https://i.imgur.com/XKb9U3D.jpeg")
            embed.add_field(
                name="🥸 Profile 🤓",
                value=f"Name: {player_name}\nID: {player_id}\n{state_info}",
                inline=False
            )
            embed.add_field(
                name="📊 Status 📊",
                value=f"{detected_status}\nGift Code: **{code}**", 
                inline=False
            )
            embed.set_thumbnail(url=a_img)
            
            hari = datetime.now().strftime("%d/%m/%Y")
            jam = datetime.now().strftime("%H:%M:%S")
            embed.set_footer(
                text=f"Date: {hari}\nTime: {jam}\n💖 Thank you for using Survy, have a great day! 💖"
            )
            
            view = self.RedeemView(self, player_id, code)
            await interaction.channel.send(embed=embed, view=view)
            return True
            
        except TimeoutException:
            return "⌛ Timeout: invalid receiving redeem response!"
        except Exception as e:
            return f"Error Sistem: {str(e)}"

    async def _restart_captcha(self, driver, interaction):
        try:
            cap_reset = await self._find_element(driver, [
                '//*[contains(@class, "reload_btn reload_btn")]',
                '//img[contains(@class, "reload_btn reload_btn")]'
            ], 'red')

            if not cap_reset:
                print("Selector isn't found!")
                return None
            
            await self.bot.loop.run_in_executor(
                None,
                lambda: driver.execute_script(""" 
                    arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});
                    arguments[0].style.border = '3px solid red';
                    """, cap_reset)
            )

            await self.bot.loop.run_in_executor(
            None,
            lambda: driver.execute_script("arguments[0].click();", cap_reset)
            )
            await asyncio.sleep(3)
            
            re_captcha_element = await self._find_element(driver, [
                '//img[contains(@src, "data:image") and contains(@class, "verify")]',
                '//img[contains(@src, "jpeg;base64")]',
                '//div[contains(@class, "captcha")]//img',
                '//img[@alt="captcha"]',
                '//div[@data-v-781897ff]//img'
            ], 'purple')

            if not re_captcha_element:
                print("Element for CAPTCHA is not found")
                return None

            new_captcha_file = 're_captcha.png'
            await self.bot.loop.run_in_executor(
                None,
                lambda: re_captcha_element.screenshot(new_captcha_file)
            )
            mention = interaction.user.mention
            await interaction.channel.send(f"👤 |{mention}`Here's your re-CAPTCHA code`\n⏳ |`Please input the code correctly within [60s]`")
            await interaction.channel.send(file=discord.File(new_captcha_file))

            def check(rm):
                return rm.author == interaction.user and rm.channel == interaction.channel
            
            try:
                re_msg = await self.bot.wait_for('message', timeout=60.0, check=check)
                re_final_text = re_msg.content.strip()[:4]
                
                if len(re_final_text) != 4 or not re_final_text.isalnum():
                    await self._send_msg(interaction, "⚠️ Captcha format is invalid! Please input 4 numerics characters.")
                    return None
                    
                print(f"CAPTCHA: {re_final_text} inputted")

                input_field = await self.bot.loop.run_in_executor(
                    None,
                    lambda: WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, '//input[contains(@placeholder, "Enter verification code")]')
                        )
                    )
                )

                await asyncio.sleep(0.5)
                await self._input_text(driver, input_field,re_final_text)
                return re_final_text

            except asyncio.TimeoutError:
                await interaction.followup.send("⏰ Input Timeout!")
                return None

        except Exception as e:
            print(f"Invalid CAPTCHA: {str(e)}")
            return None

    # Command handlers
    @app_commands.command(
        name="predeem",
        description="Will redeem your Whiteout Survival gift-code personally",
    )
    @app_commands.describe(
        player_id="Player ID",
        code="Gift-code"
    )
    async def personal_redeem(self, interaction: discord.Interaction, player_id: str, code: str):
        if interaction.channel.id not in self.CHANNEL_ID:
            await interaction.response.send_message(
                "❌ Survy commands can only be used on certain channel!")
            return
        await interaction.response.defer(thinking=True) 
        driver = self.setup_driver()
        
        try:
            # Execute redemption flow
            await interaction.followup.send("LET'S BEGIN!")
            await asyncio.sleep(0.2)
            await interaction.channel.send("🤖 |`Starting your personal redeem`\n🍳 |`Let me cook for you ~`")
            if not await self._open_website(driver):
                return

            if not await self._input_player_id(driver, player_id):
                return

            if not await self._login(driver):
                return

            if not await self._input_gift_code(driver, code):
                return
            
            captcha_result = await self._solve_captcha(driver, interaction)
            if not captcha_result:
                return

            if not await self._confirm_redemption(driver):
                return

            await interaction.channel.send("🎉 |`Here's your redeem result!`")
            await asyncio.sleep(0.5)
            await self._get_redemption_result(driver, player_id, code, interaction)

        except Exception as e:
            await interaction.followup.send(f"💀 Fatal Error: {str(e)}")
        finally:
            await self.bot.loop.run_in_executor(None, driver.quit)

async def setup(bot):
    await bot.add_cog(PersonalRedeem(bot))