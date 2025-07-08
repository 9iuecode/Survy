import discord
import asyncio
import traceback
import os
import sqlite3
import aiosqlite
from datetime import datetime
from pathlib import Path
from discord.ext import commands
from discord import app_commands, ui
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from typing import Dict, List

class GroupRedeem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.CHANNEL_ID = [1364460757084930101]
        self.OSBC = 1095916483370029128
        self.REDEEM_URL = 'https://wos-giftcode.centurygame.com/'
        self.db_path = Path('data/group_redeem.db')

        os.makedirs('data', exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_groups (
                    user_id TEXT NOT NULL,
                    group_name TEXT NOT NULL,
                    player_ids TEXT NOT NULL,
                    PRIMARY KEY (user_id, group_name)
                )
            """)
            conn.commit()
    
    async def load_user_groups(self, user_id: str) -> Dict[str, List[str]]:
        groups = {}
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT group_name, player_ids FROM user_groups WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                for group_name, ids_str in rows:
                    groups[group_name] = ids_str.split(',')
        return groups
    
    async def save_user_group(self, user_id: str, group_name: str, player_ids: List[str]):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO user_groups (user_id, group_name, player_ids)
                VALUES (?, ?, ?)
                """,
                (user_id, group_name, ','.join(player_ids))
            )
            await db.commit()
    
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
    
    async def execute_group_redemption(self, interaction: discord.Interaction, user_id: str, group_name: str, code: str):
        user_groups = await self.load_user_groups(user_id)
        if group_name not in user_groups:
            await interaction.followup.send("❌ Group not found!", ephemeral=True)
            return
        mention = interaction.user.mention
        group_ids = user_groups.get(group_name, [])
        driver = None
        
        try:
            results = []
            await interaction.channel.send(f"🤖 |**`STARTING TO REDEEM`**\n😇 |`PLEASE WAIT AND FOLLOW OUR INSTRUCTIONS,` {mention}")            
            for player_id in group_ids:
                driver = self.setup_driver()
                
                try:
                    await interaction.channel.send(f"🆔 |`PROCESSING ID: {player_id}`\n🏂 |`HERE YOU GO ~`")
                    await asyncio.sleep(0.5)
                    
                    if not await self.open_website(driver):
                        results.append(f"❌ {player_id}: Failed opening website")
                        continue
                    
                    if not await self.input_player_id(driver, player_id):
                        results.append(f"❌ {player_id}: Invalid ID")
                        continue
                    
                    if not await self.login(driver):
                        results.append(f"❌ {player_id}: Failed to login")
                        continue
                    
                    if not await self.input_gift_code(driver, code):
                        results.append(f"❌ {player_id}: Invalid gift code")
                        continue
                    
                    captcha_result = await self.captcha_solver(driver, interaction)
                    if not captcha_result:
                        results.append(f"❌ {player_id}: Invalid captcha")
                        continue
                    
                    if not await self.confirm_for_redeem(driver):
                        results.append(f"❌ {player_id}: Failed to confirm")
                        continue
                    
                    
                    result_element = await self.find_element(driver, [
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
                        results.append(f"❌ {player_id}: Cannot find redeem result")
                        continue
                    
                    
                    message_text = await self.bot.loop.run_in_executor(
                        None,
                        lambda: result_element.get_attribute('textContent').strip()
                    )
                    
                    status_map = {
                        'Redeemed': '✅ **Successful**: Gift code redeemed.',
                        'Code expired': '❌ **Error**: Captcha code expired.',
                        'Incorrect': '❌ **Error**: Captcha code incorrect.',
                        'Please': '⚠️ **Warning**: Please relog-in with correct character!',
                        'already': '❎ **Error**: Code was already claimed.',
                        'not found': '❌ **Error**: Gift code was not found.',
                        'Expired': '✖️ **Error**: Gift code expired, unable to claim.',
                        'Claim': '✖️ **Error**: Claim limit reached.'
                    }
                    
                    detected_status = "⚠️ Unknown status"
                    for keyword, status in status_map.items():
                        if keyword.lower() in message_text.lower():
                            detected_status = status
                            break
                    
                    try:
                        player_name = await self.bot.loop.run_in_executor(
                            None,
                            lambda: driver.find_element(By.XPATH, '//p[contains(@class, "name")]').text
                        )
                    except:
                        player_name = "Unknown"
                    
                    results.append(f"{detected_status} - {player_name} (`{player_id}`)")
                    
                except Exception as e:
                    results.append(f"💀 {player_id}: Error - {str(e)}")
                    traceback.print_exc()
                finally:
                    await interaction.channel.send(f"✅ |`{player_id} IS DONE`")
                    if driver:
                        await self.bot.loop.run_in_executor(None, driver.quit)
                    await asyncio.sleep(0.5)

            red_count = all("❌" in r for r in results)
            yellow_count = any("⚠️" in r or "✖️" in r or "❎" in r for r in results)

            if red_count:
                color = discord.Color.red()
            elif yellow_count:
                color = discord.Color.orange()
            else:
                color = discord.Color.green()

            embed = discord.Embed(
                title=f"[{group_name} GROUP] | RESULTS:",
                description="\n".join(results),
                color=color
            )
            embed.set_author(
                name="Survy REDEEM",
                icon_url="https://i.imgur.com/XKb9U3D.jpeg"
            )
            hari = datetime.now().strftime("%d/%m/%Y")
            jam = datetime.now().strftime("%H:%M:%S")
            embed.set_footer(
                text=f"Date: {hari}\nTime: {jam}\n💖 Thank you for using Survy, have a great day! 💖"
            )
            await interaction.channel.send(f"☄️ |`ALL {len(group_ids)} IDS IN [{group_name}] GROUP IS DONE`")
            await asyncio.sleep(1)
            await interaction.channel.send(f"🎉 |`HERE'S YOUR REDEEM RESULTS!` {mention}")
            await interaction.channel.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(
                f"💀 Error fatal: {str(e)}",
                ephemeral=True
            )
            traceback.print_exc()
        finally:
            if driver:
                await self.bot.loop.run_in_executor(None, driver.quit)

    async def rename_user_group(self, user_id: str, new_name: str, old_name: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE user_groups SET group_name = ? WHERE user_id = ? AND group_name = ?",
                (new_name, user_id, old_name)
            )
            await db.commit()
    
    async def add_new_ids(self, user_id: str, group_name: str, new_ids: List[str]):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT player_ids FROM user_groups WHERE user_id = ? AND group_name = ?",
                (user_id, group_name)
            ) as cursor:
                comma = await cursor.fetchone()

            existing_ids = comma[0].split(',')
            updated_ids = list(set(existing_ids + new_ids))

            await db.execute(
                "UPDATE user_groups SET player_ids = ? WHERE user_id = ? AND group_name = ?",
                (','.join(updated_ids), user_id, group_name)
            )
            await db.commit()

    async def delete_ids(self, user_id: str, group_name: str, ids_remove: List[str]):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT player_ids FROM user_groups WHERE user_id = ? AND group_name = ?",
                (user_id, group_name)
            ) as cursor:
                comma = await cursor.fetchone()

            existing_ids = comma[0].split(',')
            updated_ids = [pid for pid in existing_ids if pid not in ids_remove]

            if not updated_ids:
                raise ValueError("Cannot delete all ids in one group")

            await db.execute(
                "UPDATE user_groups SET player_ids = ? WHERE user_id = ? AND group_name = ?",
                (','.join(updated_ids), user_id, group_name)
            )
            await db.commit()

    async def delete_user_group(self, user_id: str, group_name: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            try:
                async with db.execute(
                    "SELECT 1 FROM sqlite_master WHERE type= 'table' AND name= 'user_groups'"
                ) as cursor:
                    if not await cursor.fetchone():
                        raise ValueError("table 'user_groups' does not exist")
                
                await db.execute(
                    "DELETE FROM user_groups WHERE user_id = ? AND group_name = ?",
                    (user_id, group_name)
                )
                await db.commit()
                
                async with db.execute(
                    "SELECT 1 FROM user_groups WHERE user_id = ? AND group_name = ?",
                    (user_id, group_name)
                ) as cursor:
                    return not await cursor.fetchone()
            except aiosqlite.Error as e:
                print(f"[Database Error] failed to delete: {str(e)}")
                return False
        
    class GroupList(ui.Select):
        def __init__(self, groups: Dict[str, List[str]]):
            options = [
                discord.SelectOption(
                    label=f"📁 {group_name}",
                    description=f"{len(ids)} IDs | Tap to view",
                    value=group_name
                ) for group_name, ids in groups.items()
            ]

            super().__init__(
                placeholder="Select action",
                options=options,
                max_values=1
            )

        async def callback(self, interaction: discord.Interaction):
            cog = interaction.client.get_cog("GroupRedeem")
            user_id = str(interaction.user.id)
            group_name = self.values[0]
            user_groups = await cog.load_user_groups(user_id)

            embed = discord.Embed(
                title=f"Group: {group_name}",
                description=f"Members: {len(user_groups[group_name])}"
            )

            embed.add_field(
                name="Player IDs",
                value="\n".join(user_groups[group_name]) or "No members",
                inline=False
            )
        
            view = cog.GroupActionView(group_name)
            await interaction.response.send_message(
                embed=embed,
                view=view,
                ephemeral=False
            )

    class CreateGroupModal(ui.Modal, title="Create New Group"):
        group_name = ui.TextInput(
            label="Group Name", 
            placeholder="Example: Team ABC",
            max_length=30)
        
        player_ids = ui.TextInput(
            label="Player IDs with (',') max 10",
            placeholder="Example: 1234567,1234589",
            style=discord.TextStyle.paragraph,
            max_length=200
        )

        async def on_submit(self, interaction: discord.Interaction):
            cog = interaction.client.get_cog("GroupRedeem")
            user_id = str(interaction.user.id)

            if not self.group_name.value.strip():
                await interaction.response.send_message(
                    "❌ Group name cannot be empty!",
                    ephemeral=True
            )
                return

            raw_ids = [id.strip() for id in self.player_ids.value.split(',')]
            id_list = []
            
            for player_id in raw_ids[:50]:
                if player_id and player_id.isdigit() and len(player_id) >= 7:
                    id_list.append(player_id)
                else:
                    await interaction.response.send_message(
                        f"⚠️ Removed invalid ID: {player_id}",
                        ephemeral=True
                    )
            
            if not id_list:
                await interaction.response.send_message(
                    "❌ No valid player IDs provided!",
                    ephemeral=True
            )
                return
            
            try:
                existing_groups = await cog.load_user_groups(user_id)
                
                
                if self.group_name.value.strip() in existing_groups:
                    await interaction.response.send_message(
                        f"❌ Group name '{self.group_name.value}' already exists!",
                        ephemeral=True
                    )
                    return
                
                await cog.save_user_group(
                    user_id=str(interaction.user.id),
                    group_name=self.group_name.value.strip(),
                    player_ids=id_list
                )

                await interaction.response.send_message(
                    f"✅ Group **{self.group_name.value}** created with {len(id_list)} IDs!"
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Failed to create group: {str(e)}",
                    ephemeral=True
                )
                traceback.print_exc()

    class RenameGroupModal(ui.Modal, title="Rename Group Name"):
        def __init__(self, old_name: str):
            super().__init__()
            self.old_name = old_name
            self.new_name = ui.TextInput(
                label="New Name",
                placeholder=f"Previous Name: {old_name}",
                default=old_name
            )

            self.add_item(self.new_name)

        async def on_submit(self, interaction: discord.Interaction):
            cog = interaction.client.get_cog("GroupRedeem")
            new_name = self.new_name.value.strip()

            if not new_name:
                return await interaction.channel.send("❌ Name cannot be empty")
            
            if new_name == self.old_name:
                return await interaction.channel.send("⚠️ New name cannot be same as previous name")
            
            try:
                await cog.rename_user_group(
                    user_id=str(interaction.user.id),
                    old_name=self.old_name,
                    new_name=new_name
                )

                await interaction.response.send_message(f"✅ Group name has been successfully changed to **{new_name}**")
            except Exception as e:
                await interaction.response.send_message(f"❌ Failed to rename: {str(e)}", ephemeral=True)
            
    class AddIdModal(ui.Modal, title="Add New Member Id"):
        def __init__(self, group_name: str):
            super().__init__()
            self.group_name = group_name
            self.new_ids = ui.TextInput(
                label="Player Id (Seperate with comma ',')",
                placeholder="Example: 123456, 789101",
                style=discord.TextStyle.paragraph
            )
            self.add_item(self.new_ids)

        async def on_submit(self, interaction:discord.Interaction):
            cog = interaction.client.get_cog("GroupRedeem")
            raw_ids = [id.strip() for id in self.new_ids.value.split(',')]
            valid_ids = []

            for pid in raw_ids:
                if pid.isdigit() and len(pid) >= 7:
                    valid_ids.append(pid)
                else:
                    await interaction.channel.send(f"⚠️ {pid} is invalid")
                
            if not valid_ids:
                return print("There's no valid id")
            
            try:
                await cog.add_new_ids(
                    user_id=str(interaction.user.id),
                    group_name=self.group_name,
                    new_ids=valid_ids
                )
                
                await interaction.channel.send(f"✅ Successfully added {len(valid_ids)} to **{self.group_name}**")
            except Exception as e:
                await interaction.response.send_message(f"❌ Failed to add ids: {str(e)}", ephemeral=True)
    
    class DeleteIds(ui.Select):
        def __init__(self, group_name: str, current_ids: List[str]):
            options = [
                discord.SelectOption(
                    label=f"ID: {pid}",
                    value=pid,
                    description="Click to delete"
                ) for pid in current_ids
            ]

            super().__init__(
                placeholder="Select id you want to remove..",
                options=options,
                max_values=len(options)
            )
            self.group_name = group_name
        
        async def callback(self, interaction: discord.Interaction):
            cog = interaction.client.get_cog("GroupRedeem")
            remove_ids = self.values

            try:
                await cog.delete_ids(
                    user_id=str(interaction.user.id),
                    group_name=self.group_name,
                    ids_remove=remove_ids
                )

                await interaction.channel.send(f"✅ Successfully deleted {len(remove_ids)} from **{self.group_name}**")
            except Exception as e:
                await interaction.response.send_message(f"❌ Failed to remove: {str(e)}")

    class GroupActionView(ui.View):
        def __init__(self, group_name: str):
            super().__init__()
            self.group_name = group_name

            self.add_item(ui.Button(
                style=discord.ButtonStyle.green,
                label="Redeem",
                emoji="🎁",
                custom_id=f"redeem_{group_name}"
            ))

            self.add_item(ui.Button(
                style=discord.ButtonStyle.blurple,
                label="Edit",
                emoji="✏️",
                custom_id=f"edit_{group_name}"
            ))

            self.add_item(ui.Button(
                style=discord.ButtonStyle.red,
                label="Delete",
                emoji="🗑️",
                custom_id=f"delete_{group_name}"
            ))

    class EditGroupView(ui.View):
        def __init__(self, group_name: str):
            super().__init__()
            self.group_name = group_name

            self.add_item(ui.Button(
                style=discord.ButtonStyle.blurple,
                label="Rename",
                emoji="📝",
                custom_id=f"rename_{group_name}"
            ))

            self.add_item(ui.Button(
                style=discord.ButtonStyle.blurple,
                label="Add Member",
                emoji="🅰️",
                custom_id=f"add_mem_{group_name}"
            ))

            self.add_item(ui.Button(
                style=discord.ButtonStyle.red,
                label="Delete Member",
                emoji="💣",
                custom_id=f"delete_mem_{group_name}"
            ))

    class DeleteGroupView(ui.View):
        def __init__(self, group_name: str):
            super().__init__(timeout=30)
            self.group_name = group_name

            confirm_button = (ui.Button(
                style=discord.ButtonStyle.red,
                label="YES",
                emoji="💥",
                custom_id=f"confirm_delete_{group_name}"
            ))

            confirm_button.callback = self.confirm_callback
            self.add_item(confirm_button)

            cancel_button = (ui.Button(
                style=discord.ButtonStyle.gray,
                label="Cancel",
                emoji="🔙",
                custom_id=f"cancel_delete_{group_name}"
            ))

            cancel_button.callback = self.cancel_callback
            self.add_item(cancel_button)

        async def confirm_callback(self, interaction: discord.Interaction):
            cog = interaction.client.get_cog("GroupRedeem")
            success = await cog.delete_user_group(
                user_id=str(interaction.user.id),
                group_name=self.group_name
            )
            
            if success:
                await interaction.response.edit_message(
                    content = f"✅ Successfully Deleted **{self.group_name}** Group",
                    embed=None,
                    view=None
                )
            
            else:
                await interaction.response.edit_message(
                    content = f"❌ Failed to Delete **{self.group_name}** Group",
                    embed=None,
                    view=None
                )
        async def cancel_callback(self, interacion: discord.Interaction):
            await interacion.response.edit_message(
                content = f"🔃 Delete Canceled on **{self.group_name}** Group",
                embed=None,
                view=None,
                delete_after=3
            )
            
    class GroupSelection(ui.Select):
        def __init__(self,  groups: Dict[str, List[str]]):
            options = [
                discord.SelectOption(label="Create a group", value="new", emoji="🆕"),
                discord.SelectOption(label="Group list", value="list", emoji="📃")
            ]

            for group_name, members in groups.items():
                options.append(
                    discord.SelectOption(
                        label=f"📁 {group_name}", 
                        value=f"group_{group_name}",
                        description=f"{len(members)} IDs | Click to view"
                    )
                )
            
            super().__init__(
                placeholder="Select action..",
                options=options,
                max_values=1
            )


        async def callback(self, interaction: discord.Interaction):
            cog = interaction.client.get_cog("GroupRedeem")
            selected = self.values[0]
            if self.values[0] == "new":
                await interaction.response.send_modal(cog.CreateGroupModal())
            
            elif self.values[0] == "list":
                user_groups = await cog.load_user_groups(str(interaction.user.id))
                if not user_groups:
                    await interaction.response.send_message(
                        "❌ You don't have any groups yet!",
                        ephemeral=True
                    )
                    return

                view = ui.View()
                view.add_item(cog.GroupList(user_groups))
                await interaction.response.send_message(
                    "📋 Group list: ",
                    view=view
                )
            
            elif selected.startswith("group_"):
                group_name = selected[6:]
                user_groups = await cog.load_user_groups(str(interaction.user.id))

                if group_name in user_groups:
                    embed = discord.Embed(
                        title=f"Group: {group_name}",
                        description=f"Members: {len(user_groups[group_name])}"
                    )

                    embed.add_field(
                        name="Player IDs",
                        value="\n".join(user_groups[group_name]) or "No members",
                        inline=False
                    )
                
                    view = cog.GroupActionView(group_name)
                    await interaction.response.send_message(
                        embed=embed,
                        view=view,
                        ephemeral=False
                    )

    class GroupRedeemModal(ui.Modal, title="Group Redemption"):
        def __init__(self, cog, user_id: str, group_name: str):
            super().__init__()
            self.cog = cog
            self.user_id = user_id
            self.group_name = group_name
            self.code = ui.TextInput(
                label="Gift Code",
                placeholder="Enter a gift code",
                max_length=20
            )
            self.add_item(self.code)

        async def on_submit(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            
            await self.cog.execute_group_redemption(
                interaction=interaction,
                user_id=self.user_id,
                group_name=self.group_name,
                code=self.code.value
            )
                

    @app_commands.command(
        name="gredeem",
        description="Make a group and do multiple redeem in one flow"
    )
    async def group_redeem(self, interaction: discord.Interaction):
        if interaction.channel.id not in self.CHANNEL_ID:
            await interaction.response.send_message(
                "❌ Command can only be used in specific channels!",
                ephemeral=True
            )
            return

        user_groups = await self.load_user_groups(str(interaction.user.id))
        view = ui.View()
        view.add_item(self.GroupSelection(user_groups))
        
        await interaction.response.send_message(
            "🎪 Group redeem menu:",
            view=view
        )

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        try:
            if not interaction.data or "custom_id" not in interaction.data:
                return

            custom_id = interaction.data["custom_id"]
            user_id = str(interaction.user.id)

            if custom_id.startswith("redeem_"):
                group_name = custom_id[7:]
                user_groups = await self.load_user_groups(user_id)
                if group_name not in user_groups:
                    await interaction.channel.send("❌ Group not found!")
                    return
            
                await interaction.response.send_modal(self.GroupRedeemModal(self, user_id, group_name))
            
            elif custom_id.startswith("edit_"):
                group_name = custom_id[5:]
                user_groups = await self.load_user_groups(user_id)
                if group_name not in user_groups:
                    await interaction.channel.send("❌ Group not found!")
                
                view = self.EditGroupView(group_name)
                await interaction.channel.send(
                    f"Editing **{group_name}** Group",
                    view=view
                )
            
            elif custom_id.startswith("rename_"):
                group_name = custom_id[7:]
                await interaction.response.send_modal(
                    self.RenameGroupModal(old_name=group_name)
                )
            
            elif custom_id.startswith("add_mem_"):
                group_name = custom_id[8:]
                await interaction.response.send_modal(
                    self.AddIdModal(group_name=group_name)
                )
            
            elif custom_id.startswith("delete_mem_"):
                group_name = custom_id[11:]
                user_groups = await self.load_user_groups(user_id)

                if group_name not in user_groups:
                    await interaction.channel.send("❌ Group not found")
                
                if not user_groups[group_name]:
                    await interaction.channel.send("❌ Group has no member")
                
                view = ui.View()
                view.add_item(self.DeleteIds(group_name, user_groups[group_name]))
                await interaction.response.send_message(
                    f"Select members to remove from **{group_name}**:",
                    view=view
                )

            elif custom_id.startswith("delete_"):
                group_name = custom_id[7:]
                user_groups = await self.load_user_groups(user_id)

                if group_name not in user_groups:
                    await interaction.channel.send("❌ Group isn't there")
                
                del_confirm = discord.Embed(
                    description=f"🥲 Are you sure wanted to delete **{group_name}** from your list?",
                    color=discord.Color.red()
                )

                view = self.DeleteGroupView(group_name)
                await interaction.response.send_message(
                    embed=del_confirm,
                    view=view
                )
                
        except Exception as e:
            print(f"Error handling interaction: {str(e)}")
            traceback.print_exc()

    # ========== SUPPORT FUNCTIONS ===========
    async def send_message(self, content: str, interaction: discord.Interaction = None, ephemeral: bool = True):
        """Fungsi terpadu untuk mengirim pesan"""
        try:
            if interaction:
                if interaction.response.is_done():
                    await interaction.followup.send(content, ephemeral=ephemeral)
                else:
                    await interaction.response.send_message(content, ephemeral=ephemeral)
            else:
                channel = self.bot.get_channel(self.CHANNEL_ID[0])
                await channel.send(content)
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
    
    async def send_file(self, file_path: str, interaction: discord.Interaction):
        """Fungsi untuk mengirim file ke Discord"""
        try:
            with open(file_path, 'rb') as f:
                if interaction.response.is_done():
                    await interaction.followup.send(file=discord.File(f))
                else:
                    await interaction.response.send_message(file=discord.File(f))
            return True
        except Exception as e:
            print(f"Error sending file: {e}")
            await self.send_message("❌ Failed to send file!", interaction)
            return False
        
    async def web_page_load(self, driver):
        await self.bot.loop.run_in_executor(
            None,
            lambda: WebDriverWait(driver, 30).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
        )
    
    async def find_element(self, driver, selectors, highlight_color='red'):
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
    
    async def input_text(self, driver, element, text):
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
    
    async def mouse_movement(self, driver, x=150, y=300):
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

    # ========== MAIN FUNCTIONS ===========
    async def open_website(self, driver):
        await self.bot.loop.run_in_executor(None, lambda: driver.get(self.REDEEM_URL))
        await asyncio.sleep(0.5)
        return True
        
    
    async def input_player_id(self, driver, player_id):
        await self.web_page_load(driver)
        await self.mouse_movement(driver, 100, 200)

        id_field = await self.find_element(driver, [
            '//input[@data-v-781897ff]',
            '//input[@placeholder="Player ID"]',
            '//input[contains(@id,"player")]',
            '//input[@type="text"][@maxlength="10"]'
        ], 'red')

        if not id_field:
            print("ID Selector Not Found")
            return False
        
        await self.input_text(driver, id_field, player_id)
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
    
    async def login(self, driver):
        await self.web_page_load(driver)

        login_button = await self.find_element(driver, [
            '//button[@data-v-781897ff]',
            '//button[@class="btn login_btn"]',
            '//button[contains(@class,"btn login_btn")]',
            '//span[@data-v-781897ff]',
            '//span[contains(text(), "Login")]'
        ], 'lime')

        if not login_button:
            print("Login Selector Not Found")
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
        await asyncio.sleep(1.5)
        return True
    
    async def input_gift_code(self, driver, code):
        await self.web_page_load(driver)
        await self.mouse_movement(driver)

        code_field = await self.find_element(driver, [
            '//input[@data-v-781897ff]',
            '//input[@class="input_wrap"]',
            '//input[@placeholder="Enter Gift Code"]',
            '//input[@type="text"][@maxlength="20"]'
        ], 'green')

        if not code_field:
            print("GiftCode Selector Not Found")
            return False
        
        await self.input_text(driver, code_field, code)
        print(f"Successfully input: {code} as a gift code!")
        await asyncio.sleep(0.5)
        return True
    
    async def captcha_solver(self, driver, interaction):
        try:
            captcha_element = await self.find_element(driver, [
                '//img[contains(@src, "data:image") and contains(@class, "verify")]',
                '//img[contains(@src, "jpeg;base64")]',
                '//div[contains(@class, "captcha")]//img',
                '//img[@alt="captcha"]',
                '//div[@data-v-781897ff]//img'
            ], 'yellow')

            if not captcha_element:
                await self.send_message("❌ Could not find captcha element!", interaction)
                return False
            
            captcha_file = 'captcha.png'
            mention = interaction.user.mention
            try:
                await self.bot.loop.run_in_executor(
                    None,
                    lambda: captcha_element.screenshot(captcha_file)
                )
                
                if not os.path.exists(captcha_file):
                    await self.send_message("❌ Failed to create captcha image!", interaction)
                    return False
                await interaction.channel.send(f"👤 |{mention}, `HERE IS THE CAPTCHA`\n⌛ |`PLEASE INPUT THE CODE WITHIN 60s:`")
                await interaction.channel.send(file=discord.File(captcha_file))
                
            except Exception as e:
                print(f"Error saving captcha: {e}")
                await self.send_message("❌ Error processing captcha image!", interaction)
                return False

            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel
            
            try:
                msg = await self.bot.wait_for('message', timeout=60.0, check=check)
                final_text = msg.content.strip()[:4]
                
                if len(final_text) != 4:
                    await self.send_message("⚠️ Invalid format! Please enter exactly 4 characters!", interaction)
                    return None
                
                if not final_text.isalnum():
                    await self.send_message("⚠️ Only letters and numbers are allowed!", interaction)
                    return None
                
                input_field = await self.find_element(driver, [
                    '//input[contains(@placeholder, "Enter verification code")]',
                    '//input[@type="text" and @maxlength="4"]'
                ])
                
                if not input_field:
                    await self.send_message("❌ Could not find captcha input field!", interaction)
                    return None

                await self.input_text(driver, input_field, final_text)
                return final_text

            except asyncio.TimeoutError:
                await self.send_message("⏰ Timeout! No captcha input received.", interaction)
                return None
            
        except Exception as e:
            print(f"Captcha solver error: {traceback.format_exc()}")
            await self.send_message("💀 Error in captcha process!", interaction)
            return None
        finally:
            if os.path.exists(captcha_file):
                try:
                    os.remove(captcha_file)
                except:
                    pass
        
    async def confirm_for_redeem(self, driver):
        confirm_button = await self.find_element(driver, [
            '//*[contains(@class, "btn exchange_btn") and contains(text(), "Confirm")]',
            '//div[contains(@class, "btn exchange_btn") and contains(text(), "Confirm")]'
        ], 'lime')

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

    

async def setup(bot):
    await bot.add_cog(GroupRedeem(bot))