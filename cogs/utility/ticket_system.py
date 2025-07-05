import discord
from discord.ext import commands
from discord import app_commands, ui
import logging
import os
import datetime
import asyncio
import json
# import aiofiles # This import would be preferred for async file operations
# import asyncio # Keep asyncio for async functions

# JSON file paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
SETTINGS_DIR = os.path.join(DATA_DIR, 'ticket_settings')
TICKETS_DIR = os.path.join(DATA_DIR, 'active_tickets')

logger = logging.getLogger(__name__)

# Mapping common color names to discord.Color objects
COLOR_MAP = {
    'default': discord.Color.default(),
    'teal': discord.Color.teal(),
    'dark_teal': discord.Color.dark_teal(),
    'green': discord.Color.green(),
    'dark_green': discord.Color.dark_green(),
    'blue': discord.Color.blue(),
    'dark_blue': discord.Color.dark_blue(),
    'purple': discord.Color.purple(),
    'dark_purple': discord.Color.dark_purple(),
    'magenta': discord.Color.magenta(),
    'dark_magenta': discord.Color.dark_magenta(),
    'gold': discord.Color.gold(),
    'dark_gold': discord.Color.dark_gold(),
    'orange': discord.Color.orange(),
    'dark_orange': discord.Color.dark_orange(),
    'red': discord.Color.red(),
    'dark_red': discord.Color.dark_red(),
    'lighter_grey': discord.Color.lighter_grey(),
    'dark_grey': discord.Color.dark_grey(),
    'darker_grey': discord.Color.darker_grey(),
    'light_grey': discord.Color.light_grey(),
    'blurple': discord.Color.blurple(),
    'greyple': discord.Color.greyple()
}


# --- JSON File Handling Helpers ---

async def _ensure_dirs_exist():
    """Ensures the necessary directories for JSON files exist."""
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    os.makedirs(TICKETS_DIR, exist_ok=True)
    #logger.info("Ensured ticket data directories exist.") # Avoid excessive logging

def _get_settings_filepath(guild_id: int):
    """Returns the filepath for a guild's ticket settings JSON."""
    return os.path.join(SETTINGS_DIR, f'{guild_id}.json')

def _get_tickets_filepath(guild_id: int):
    """Returns the filepath for a guild's active tickets JSON."""
    return os.path.join(TICKETS_DIR, f'tickets_{guild_id}.json')

async def _load_json_file(filepath: str, default_data):
    """Loads data from a JSON file. Returns default_data if file not found or empty/invalid."""
    await _ensure_dirs_exist() # Ensure directories exist before trying to read

    # Simulating async file read with sync os.path.exists and open
    if not os.path.exists(filepath):
        return default_data
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content or content.strip() == "":
                return default_data
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
        logger.error(f"Error loading JSON file {filepath}: {e}", exc_info=True)
        return default_data

async def _save_json_file(filepath: str, data):
    """Saves data to a JSON file, overwriting existing content."""
    await _ensure_dirs_exist() # Ensure directories exist before trying to write

    # Simulating async file write with sync open
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving JSON file {filepath}: {e}", exc_info=True)
        return False

# --- Funções Auxiliares para Embeds (Reutilizadas do Welcome/Leave) ---
def _create_embed_from_data(embed_data: dict, member: discord.Member = None, guild: discord.Guild = None):
    """Cria um discord.Embed a partir de um dicionário de dados, formatando variáveis."""
    embed = discord.Embed()
    
    if embed_data.get('title'):
        embed.title = embed_data['title'].format(
            member=member,
            guild=guild,
            member_name=member.display_name if member else 'N/A',
            member_count=guild.member_count if guild else 'N/A'
        )
    else:
        embed.title = ""

    if embed_data.get('description'):
        embed.description = embed_data['description'].format(
            member=member,
            guild=guild,
            member_name=member.display_name if member else 'N/A',
            member_count=guild.member_count if guild else 'N/A'
        )
    else:
        embed.description = ""
    
    if embed_data.get('color') is not None:
        try:
            color_value = embed_data['color']
            if isinstance(color_value, str):
                color_str = color_value.strip().lower() # Convert to lowercase for map lookup
                if color_str in COLOR_MAP:
                    embed.color = COLOR_MAP[color_str]
                elif color_str.startswith('#'):
                    embed.color = discord.Color(int(color_str[1:], 16))
                elif color_str.startswith('0x'):
                    embed.color = discord.Color(int(color_str, 16))
                else:
                     # Fallback to attempt decimal conversion if not a recognized name or hex
                    try:
                        embed.color = discord.Color(int(color_str))
                    except ValueError:
                        logging.warning(f"Cor inválida no embed (formato desconhecido): {color_value}. Usando cor padrão.")
                        embed.color = discord.Color.default()
            elif isinstance(color_value, int):
                embed.color = discord.Color(color_value)
            else: # Handle other unexpected types
                logging.warning(f"Cor inválida no embed (tipo inesperado): {type(color_value)}. Usando cor padrão.")
                embed.color = discord.Color.default()
        except (ValueError, TypeError, Exception) as e: # Catch any other exceptions during color processing
            logging.warning(f"Erro ao processar cor do embed: {embed_data.get('color')}. Erro: {e}. Usando cor padrão.", exc_info=True)
            embed.color = discord.Color.default()
    else:
        embed.color = discord.Color.default()

    if embed_data.get('image_url'):
        embed.set_image(url=embed_data['image_url'])
    
    if embed_data.get('thumbnail_url'):
        embed.set_thumbnail(url=embed_data['thumbnail_url'])

    if embed_data.get('footer_text'):
        embed.set_footer(text=embed_data['footer_text'].format(
            member=member,
            guild=guild,
            member_name=member.display_name if member else 'N/A',
            member_count=guild.member_count if guild else 'N/A'
        ), icon_url=embed_data.get('footer_icon_url'))

    if embed_data.get('author_name'):
        embed.set_author(name=embed_data['author_name'].format(
            member=member,
            guild=guild,
            member_name=member.display_name if member else 'N/A',
            member_count=guild.member_count if guild else 'N/A'
        ), icon_url=embed_data.get('author_icon_url'))
    
    if 'fields' in embed_data:
        for field in embed_data['fields']:
            field_name = str(field.get('name', ''))
            field_value = str(field.get('value', ''))
            embed.add_field(name=field_name, value=field_value, inline=field.get('inline', False))

    return embed

# --- Views para Configuração do Painel de Tickets ---
class TicketPanelConfigView(ui.View):
    def __init__(self, parent_view: ui.View, bot: commands.Bot, guild_id: int):
        super().__init__(timeout=180) # Esta view é temporária para a sessão de configuração
        self.parent_view = parent_view
        self.bot = bot
        self.guild_id = guild_id
        self.message = None

    async def on_timeout(self):
        if self.message:
            for item in self.children:
                item.disabled = True
            await self.message.edit(content="Sessão de configuração do painel de tickets expirada.", view=self)

    async def _update_panel_display(self, interaction: discord.Interaction):
        panel_embed_data = await self._get_panel_embed_data()
        
        has_custom_data = False
        if panel_embed_data:
            for key, value in panel_embed_data.items():
                if value is not None and value != "" and key not in ["fields"]:
                    has_custom_data = True
                    break
        
        panel_embed_configured = "Sim" if has_custom_data else "Não"
        
        embed = discord.Embed(
            title="Configuração do Painel de Tickets",
            description="Ajuste o embed que aparece no canal para abrir tickets.",
            color=discord.Color.blue() # Default color for the config panel embed itself
        )
        embed.add_field(name="Embed do Painel Configurado", value=panel_embed_configured, inline=False)

        preview_embed = None
        # Create preview embed using the _create_embed_from_data function
        try:
            # Always attempt to create a preview embed if there's any data, even if it's just default
            preview_embed = _create_embed_from_data(panel_embed_data if panel_embed_data else {}, guild=interaction.guild)
            embed.add_field(name="Pré-visualização do Painel", value="Veja abaixo:", inline=False)
        except Exception as e:
            logging.error(f"Erro ao criar embed de pré-visualização para guild {self.guild_id}: {e}")
            preview_embed = discord.Embed(
                title="Erro na Pré-visualização",
                description=f"Não foi possível gerar a pré-visualização do embed. Erro: {e}",
                color=discord.Color.red()
            )
        
        embeds_to_send = [embed]
        if preview_embed:
            embeds_to_send.append(preview_embed)

        if self.message:
            await self.message.edit(embeds=embeds_to_send, view=self)
        else:
            if interaction.response.is_done():
                self.message = await interaction.followup.send(embeds=embeds_to_send, view=self, ephemeral=True)
            else:
                await interaction.response.send_message(embeds=embeds_to_send, view=self, ephemeral=True)
                self.message = await interaction.original_response()


    async def _get_panel_embed_data(self):
        settings_filepath = _get_settings_filepath(self.guild_id)
        settings = await _load_json_file(settings_filepath, default_data={})
        # Panel embed data is stored directly as a dictionary under \'panel_embed\' key
        return settings.get('panel_embed', {})

    async def _save_panel_embed_data(self, embed_data: dict):
        settings_filepath = _get_settings_filepath(self.guild_id)
        settings = await _load_json_file(settings_filepath, default_data={})

        has_content = False
        for key, value in embed_data.items():
            if value is not None and value != "" and key not in ["fields"]:
                has_content = True
                break
        
        # Store embed data directly as a dictionary or remove the key if no content
        if has_content:
            settings['panel_embed'] = embed_data
        elif 'panel_embed' in settings:
             del settings['panel_embed']

        await _save_json_file(settings_filepath, settings)

    @ui.button(label="Título do Embed", style=discord.ButtonStyle.green, row=0, custom_id="panel_embed_title")
    async def set_panel_embed_title(self, interaction: discord.Interaction, button: ui.Button):
        class PanelEmbedTitleModal(ui.Modal, title="Título do Embed do Painel"):
            def __init__(self, parent_view: ui.View, current_title: str):
                super().__init__()
                self.parent_view = parent_view
                self.add_item(ui.TextInput(label="Título", placeholder="Título do embed", style=discord.TextStyle.short, custom_id="embed_title", default=current_title, required=False))

            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.defer()
                original_view = self.parent_view
                embed_data = await original_view._get_panel_embed_data()
                embed_data['title'] = self.children[0].value if self.children[0].value.strip() else None
                await original_view._save_panel_embed_data(embed_data)
                await original_view._update_panel_display(interaction)
                await interaction.followup.send("Título do Embed do Painel atualizado!", ephemeral=True)
        
        embed_data = await self._get_panel_embed_data()
        current_title = embed_data.get('title', '') or ''
        await interaction.response.send_modal(PanelEmbedTitleModal(parent_view=self, current_title=current_title))

    @ui.button(label="Descrição do Embed", style=discord.ButtonStyle.green, row=0, custom_id="panel_embed_description")
    async def set_panel_embed_description(self, interaction: discord.Interaction, button: ui.Button):
        class PanelEmbedDescriptionModal(ui.Modal, title="Descrição do Embed do Painel"):
            def __init__(self, parent_view: ui.View, current_description: str):
                super().__init__()
                self.parent_view = parent_view
                self.add_item(ui.TextInput(label="Descrição", placeholder="Descrição do embed", style=discord.TextStyle.paragraph, custom_id="embed_description", default=current_description, required=False))

            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.defer()
                original_view = self.parent_view
                embed_data = await original_view._get_panel_embed_data()
                embed_data['description'] = self.children[0].value if self.children[0].value.strip() else None
                await original_view._save_panel_embed_data(embed_data)
                await original_view._update_panel_display(interaction)
                await interaction.followup.send("Descrição do Embed do Painel atualizada!", ephemeral=True)
        
        embed_data = await self._get_panel_embed_data()
        current_description = embed_data.get('description', '') or ''
        await interaction.response.send_modal(PanelEmbedDescriptionModal(parent_view=self, current_description=current_description))

    @ui.button(label="Cor do Embed", style=discord.ButtonStyle.green, row=0, custom_id="panel_embed_color")
    async def set_panel_embed_color(self, interaction: discord.Interaction, button: ui.Button):
        class PanelEmbedColorModal(ui.Modal, title="Cor do Embed do Painel"):
            def __init__(self, parent_view: ui.View, current_color: str):
                super().__init__()
                self.parent_view = parent_view
                self.add_item(ui.TextInput(label="Cor (Nome, Hex ou Decimal)", placeholder="Ex: red, #FF0000, 2550000", style=discord.TextStyle.short, custom_id="embed_color", default=current_color, required=False))

            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.defer()
                original_view = self.parent_view
                embed_data = await original_view._get_panel_embed_data()
                color_value = self.children[0].value.strip()
                embed_data['color'] = color_value if color_value else None # Save raw string value
                await original_view._save_panel_embed_data(embed_data)
                await original_view._update_panel_display(interaction)
                await interaction.followup.send("Cor do Embed do Painel atualizada! (Pode demorar alguns segundos para atualizar no embed de pré-visualização)", ephemeral=True)
        
        embed_data = await self._get_panel_embed_data()
        current_color = embed_data.get('color', '') or ''
        await interaction.response.send_modal(PanelEmbedColorModal(parent_view=self, current_color=current_color))

    @ui.button(label="Imagem do Embed", style=discord.ButtonStyle.green, row=1, custom_id="panel_embed_image")
    async def set_panel_embed_image(self, interaction: discord.Interaction, button: ui.Button):
        class PanelEmbedImageModal(ui.Modal, title="Imagem do Embed do Painel"):
            def __init__(self, parent_view: ui.View, current_image_url: str):
                super().__init__()
                self.parent_view = parent_view
                self.add_item(ui.TextInput(label="URL da Imagem", placeholder="URL da imagem (opcional)", style=discord.TextStyle.short, custom_id="embed_image", default=current_image_url, required=False))

            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.defer()
                original_view = self.parent_view
                embed_data = await original_view._get_panel_embed_data()
                image_url = self.children[0].value.strip()
                embed_data['image_url'] = image_url if image_url else None
                await original_view._save_panel_embed_data(embed_data)
                await original_view._update_panel_display(interaction)
                await interaction.followup.send("Imagem do Embed do Painel atualizada!", ephemeral=True)
        
        embed_data = await self._get_panel_embed_data()
        current_image_url = embed_data.get('image_url', '') or ''
        await interaction.response.send_modal(PanelEmbedImageModal(parent_view=self, current_image_url=current_image_url))

    @ui.button(label="Miniatura (Thumbnail)", style=discord.ButtonStyle.green, row=1, custom_id="panel_embed_thumbnail")
    async def set_panel_embed_thumbnail(self, interaction: discord.Interaction, button: ui.Button):
        class PanelEmbedThumbnailModal(ui.Modal, title="Miniatura do Embed do Painel"):
            def __init__(self, parent_view: ui.View, current_thumbnail_url: str):
                super().__init__()
                self.parent_view = parent_view
                self.add_item(ui.TextInput(label="URL da Miniatura", placeholder="URL da imagem miniatura (opcional)", style=discord.TextStyle.short, custom_id="embed_thumbnail", default=current_thumbnail_url, required=False))

            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.defer()
                original_view = self.parent_view
                embed_data = await original_view._get_panel_embed_data()
                thumbnail_url = self.children[0].value.strip()
                embed_data['thumbnail_url'] = thumbnail_url if thumbnail_url else None
                await original_view._save_panel_embed_data(embed_data)
                await original_view._update_panel_display(interaction)
                await interaction.followup.send("Miniatura do Embed do Painel atualizada!", ephemeral=True)
        
        embed_data = await self._get_panel_embed_data()
        current_thumbnail_url = embed_data.get('thumbnail_url', '') or ''
        await interaction.response.send_modal(PanelEmbedThumbnailModal(parent_view=self, current_thumbnail_url=current_thumbnail_url))


    @ui.button(label="Rodapé do Embed", style=discord.ButtonStyle.green, row=1, custom_id="panel_embed_footer")
    async def set_panel_embed_footer(self, interaction: discord.Interaction, button: ui.Button):
        class PanelEmbedFooterModal(ui.Modal, title="Rodapé do Embed do Painel"):
            def __init__(self, parent_view: ui.View, current_footer_text: str, current_footer_icon_url: str):
                super().__init__()
                self.parent_view = parent_view
                self.add_item(ui.TextInput(label="Texto do Rodapé", placeholder="Texto do rodapé (opcional)", style=discord.TextStyle.short, custom_id="footer_text", default=current_footer_text, required=False))
                self.add_item(ui.TextInput(label="URL do Ícone do Rodapé (Opcional)", placeholder="URL da imagem do ícone", style=discord.TextStyle.short, custom_id="footer_icon_url", default=current_footer_icon_url, required=False))

            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.defer()
                original_view = self.parent_view
                embed_data = await original_view._get_panel_embed_data()
                footer_text = self.children[0].value.strip()
                footer_icon_url = self.children[1].value.strip()
                embed_data['footer_text'] = footer_text if footer_text else None
                embed_data['footer_icon_url'] = footer_icon_url if footer_icon_url else None
                await original_view._save_panel_embed_data(embed_data)
                await original_view._update_panel_display(interaction)
                await interaction.followup.send("Rodapé do Embed do Painel atualizado!", ephemeral=True)
        
        embed_data = await self._get_panel_embed_data()
        current_footer_text = embed_data.get('footer_text', '') or ''
        current_footer_icon_url = embed_data.get('footer_icon_url', '') or ''
        await interaction.response.send_modal(PanelEmbedFooterModal(parent_view=self, current_footer_text=current_footer_text, current_footer_icon_url=current_footer_icon_url))

    @ui.button(label="Redefinir Embed", style=discord.ButtonStyle.red, row=2, custom_id="reset_panel_embed")
    async def reset_panel_embed(self, interaction: discord.Interaction, button: ui.Button):
        class ResetConfirmView(ui.View):
            def __init__(self, parent_view_ref):
                super().__init__(timeout=30) # Esta view é temporária
                self.parent_view_ref = parent_view_ref

            @ui.button(label="Confirmar Redefinição", style=discord.ButtonStyle.danger, custom_id="confirm_reset_panel_embed")
            async def confirm_reset(self, interaction_confirm: discord.Interaction, button_confirm: ui.Button):
                await interaction_confirm.response.defer(ephemeral=True)
                await self.parent_view_ref._save_panel_embed_data({})
                await self.parent_view_ref._update_panel_display(interaction_confirm)
                await interaction_confirm.followup.send("Embed do Painel redefinido para o padrão!", ephemeral=True)
                self.stop()

            @ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, custom_id="cancel_reset_panel_embed")
            async def cancel_reset(self, interaction_cancel: discord.Interaction, button_cancel: ui.Button):
                await interaction_cancel.response.defer(ephemeral=True)
                await interaction_cancel.followup.send("Redefinição do Embed do Painel cancelada.", ephemeral=True)
                self.stop()
            
        await interaction.response.send_message(
            "Tem certeza que deseja redefinir o embed do painel para o padrão? Todas as personalizações serão perdidas.",
            view=ResetConfirmView(self), ephemeral=True
        )

    @ui.button(label="Voltar ao Painel Principal", style=discord.ButtonStyle.secondary, row=2, custom_id="back_to_main_panel_from_panel_config")
    async def back_to_main_panel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

        for item in self.parent_view.children:
            item.disabled = False
        await self.parent_view._update_main_display(interaction)
        await interaction.followup.send("Retornando ao painel principal do Ticket.", ephemeral=True)


# Nova View para Configuração da Mensagem Inicial do Ticket
class TicketInitialEmbedConfigView(ui.View):
    def __init__(self, parent_view: ui.View, bot: commands.Bot, guild_id: int):
        super().__init__(timeout=180) # Esta view é temporária
        self.parent_view = parent_view
        self.bot = bot
        self.guild_id = guild_id
        self.message = None

    async def on_timeout(self):
        if self.message:
            for item in self.children:
                item.disabled = True
            await self.message.edit(content="Sessão de configuração da mensagem inicial do ticket expirada.", view=self)

    async def _update_initial_embed_display(self, interaction: discord.Interaction):
        initial_embed_data = await self._get_initial_embed_data()
        
        has_custom_data = False
        if initial_embed_data:
            for key, value in initial_embed_data.items():
                if value is not None and value != "" and key not in ["fields"]:
                    has_custom_data = True
                    break
        
        initial_embed_configured = "Sim" if has_custom_data else "Não"
        
        embed = discord.Embed(
            title="Configuração da Mensagem Inicial do Ticket",
            description="Ajuste o embed que aparece dentro do canal do ticket quando ele é aberto.",
            color=discord.Color.orange() # Default color for the initial message config panel
        )
        embed.add_field(name="Embed da Mensagem Inicial Configurado", value=initial_embed_configured, inline=False)

        preview_embed = None
         # Create preview embed using the _create_embed_from_data function
        try:
             # Always attempt to create a preview embed if there's any data, even if it's just default
            preview_embed = _create_embed_from_data(initial_embed_data if initial_embed_data else {}, guild=interaction.guild)
            embed.add_field(name="Pré-visualização da Mensagem Inicial", value="Veja abaixo:", inline=False)
        except Exception as e:
            logging.error(f"Erro ao criar embed de pré-visualização da mensagem inicial para guild {self.guild_id}: {e}")
            preview_embed = discord.Embed(
                title="Erro na Pré-visualização",
                description=f"Não foi possível gerar a pré-visualização do embed. Erro: {e}",
                color=discord.Color.red()
            )
        
        embeds_to_send = [embed]
        if preview_embed:
            embeds_to_send.append(preview_embed)

        if self.message:
            await self.message.edit(embeds=embeds_to_send, view=self)
        else:
            if interaction.response.is_done():
                self.message = await interaction.followup.send(embeds=embeds_to_send, view=self, ephemeral=True)
            else:
                await interaction.response.send_message(embeds=embeds_to_send, view=self, ephemeral=True)
                self.message = await interaction.original_response()

    async def _get_initial_embed_data(self):
        settings_filepath = _get_settings_filepath(self.guild_id)
        settings = await _load_json_file(settings_filepath, default_data={})
        # Initial embed data is stored directly as a dictionary under \'initial_embed\' key
        return settings.get('initial_embed', {})

    async def _save_initial_embed_data(self, embed_data: dict):
        settings_filepath = _get_settings_filepath(self.guild_id)
        settings = await _load_json_file(settings_filepath, default_data={})

        has_content = False
        for key, value in embed_data.items():
            if value is not None and value != "" and key not in ["fields"]:
                has_content = True
                break
        
        # Store embed data directly as a dictionary or remove the key if no content
        if has_content:
            settings['initial_embed'] = embed_data
        elif 'initial_embed' in settings:
            del settings['initial_embed']

        await _save_json_file(settings_filepath, settings)

    @ui.button(label="Título", style=discord.ButtonStyle.green, row=0, custom_id="initial_embed_title")
    async def set_initial_embed_title(self, interaction: discord.Interaction, button: ui.Button):
        class InitialEmbedTitleModal(ui.Modal, title="Título da Mensagem Inicial"):
            def __init__(self, parent_view: ui.View, current_title: str):
                super().__init__()
                self.parent_view = parent_view
                self.add_item(ui.TextInput(label="Título", placeholder="Título do embed", style=discord.TextStyle.short, custom_id="initial_embed_title_input", required=False, default=current_title))

            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.defer()
                original_view = self.parent_view
                embed_data = await original_view._get_initial_embed_data()
                embed_data['title'] = self.children[0].value if self.children[0].value.strip() else None
                await original_view._save_initial_embed_data(embed_data)
                await original_view._update_initial_embed_display(interaction)
                await interaction.followup.send("Título da Mensagem Inicial atualizado!", ephemeral=True)
        
        embed_data = await self._get_initial_embed_data()
        current_title = embed_data.get('title', '') or ''
        await interaction.response.send_modal(InitialEmbedTitleModal(parent_view=self, current_title=current_title))

    @ui.button(label="Descrição", style=discord.ButtonStyle.green, row=0, custom_id="initial_embed_description")
    async def set_initial_embed_description(self, interaction: discord.Interaction, button: ui.Button):
        class InitialEmbedDescriptionModal(ui.Modal, title="Descrição da Mensagem Inicial"):
            def __init__(self, parent_view: ui.View, current_description: str):
                super().__init__()
                self.parent_view = parent_view
                self.add_item(ui.TextInput(label="Descrição", placeholder="Descrição do embed", style=discord.TextStyle.paragraph, custom_id="initial_embed_description_input", required=False, default=current_description))

            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.defer()
                original_view = self.parent_view
                embed_data = await original_view._get_initial_embed_data()
                embed_data['description'] = self.children[0].value if self.children[0].value.strip() else None
                await original_view._save_initial_embed_data(embed_data)
                await original_view._update_initial_embed_display(interaction)
                await interaction.followup.send("Descrição da Mensagem Inicial atualizada!", ephemeral=True)
        
        embed_data = await self._get_initial_embed_data()
        current_description = embed_data.get('description', '') or ''
        await interaction.response.send_modal(InitialEmbedDescriptionModal(parent_view=self, current_description=current_description))

    @ui.button(label="Cor", style=discord.ButtonStyle.green, row=0, custom_id="initial_embed_color")
    async def set_initial_embed_color(self, interaction: discord.Interaction, button: ui.Button):
        class InitialEmbedColorModal(ui.Modal, title="Cor da Mensagem Inicial"):
            def __init__(self, parent_view: ui.View, current_color: str):
                super().__init__()
                self.parent_view = parent_view
                self.add_item(ui.TextInput(label="Cor (Nome, Hex ou Decimal)", placeholder="Ex: red, #FF0000, 2550000", style=discord.TextStyle.short, custom_id="initial_embed_color_input", required=False, default=current_color))

            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.defer()
                original_view = self.parent_view
                embed_data = await original_view._get_initial_embed_data()
                color_value = self.children[0].value.strip()
                embed_data['color'] = color_value if color_value else None # Save raw string value
                await original_view._save_initial_embed_data(embed_data)
                await original_view._update_initial_embed_display(interaction)
                await interaction.followup.send("Cor da Mensagem Inicial atualizada! (Pode demorar alguns segundos para atualizar no embed de pré-visualização)", ephemeral=True)
        
        embed_data = await self._get_initial_embed_data()
        current_color = embed_data.get('color', '') or ''
        await interaction.response.send_modal(InitialEmbedColorModal(parent_view=self, current_color=current_color))

    @ui.button(label="Imagem", style=discord.ButtonStyle.green, row=1, custom_id="initial_embed_image")
    async def set_initial_embed_image(self, interaction: discord.Interaction, button: ui.Button):
        class InitialEmbedImageModal(ui.Modal, title="Imagem da Mensagem Inicial"):
            def __init__(self, parent_view: ui.View, current_image_url: str):
                super().__init__()
                self.parent_view = parent_view
                self.add_item(ui.TextInput(label="URL da Imagem", placeholder="URL da imagem (opcional)", style=discord.TextStyle.short, custom_id="initial_embed_image_input", required=False, default=current_image_url))

            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.defer()
                original_view = self.parent_view
                embed_data = await original_view._get_initial_embed_data()
                image_url = self.children[0].value.strip()
                embed_data['image_url'] = image_url if image_url else None
                await original_view._save_initial_embed_data(embed_data)
                await original_view._update_initial_embed_display(interaction)
                await interaction.followup.send("Imagem da Mensagem Inicial atualizada!", ephemeral=True)
        
        embed_data = await self._get_initial_embed_data()
        current_image_url = embed_data.get('image_url', '') or ''
        await interaction.response.send_modal(InitialEmbedImageModal(parent_view=self, current_image_url=current_image_url))

    @ui.button(label="Miniatura (Thumbnail)", style=discord.ButtonStyle.green, row=1, custom_id="initial_embed_thumbnail")
    async def set_initial_embed_thumbnail(self, interaction: discord.Interaction, button: ui.Button):
        class InitialEmbedThumbnailModal(ui.Modal, title="Miniatura da Mensagem Inicial"):
            def __init__(self, parent_view: ui.View, current_thumbnail_url: str):
                super().__init__()
                self.parent_view = parent_view
                self.add_item(ui.TextInput(label="URL da Miniatura", placeholder="URL da imagem miniatura (opcional)", style=discord.TextStyle.short, custom_id="initial_embed_thumbnail_input", required=False, default=current_thumbnail_url))

            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.defer()
                original_view = self.parent_view
                embed_data = await original_view._get_initial_embed_data()
                thumbnail_url = self.children[0].value.strip()
                embed_data['thumbnail_url'] = thumbnail_url if thumbnail_url else None
                await original_view._save_initial_embed_data(embed_data)
                await original_view._update_initial_embed_display(interaction)
                await interaction.followup.send("Miniatura da Mensagem Inicial atualizada!", ephemeral=True)
        
        embed_data = await self._get_initial_embed_data()
        current_thumbnail_url = embed_data.get('thumbnail_url', '') or ''
        await interaction.response.send_modal(InitialEmbedThumbnailModal(parent_view=self, current_thumbnail_url=current_thumbnail_url))

    @ui.button(label="Rodapé", style=discord.ButtonStyle.green, row=1, custom_id="initial_embed_footer")
    async def set_initial_embed_footer(self, interaction: discord.Interaction, button: ui.Button):
        class InitialEmbedFooterModal(ui.Modal, title="Rodapé da Mensagem Inicial"):
            def __init__(self, parent_view: ui.View, current_footer_text: str, current_footer_icon_url: str):
                super().__init__()
                self.parent_view = parent_view
                self.add_item(ui.TextInput(label="Texto do Rodapé", placeholder="Texto do rodapé (opcional)", style=discord.TextStyle.short, custom_id="initial_embed_footer_text_input", required=False, default=current_footer_text))
                self.add_item(ui.TextInput(label="URL do Ícone do Rodapé (Opcional)", placeholder="URL da imagem do ícone", style=discord.TextStyle.short, custom_id="initial_embed_footer_icon_url_input", required=False, default=current_footer_icon_url))

            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.defer()
                original_view = self.parent_view
                embed_data = await original_view._get_initial_embed_data()
                footer_text = self.children[0].value.strip()
                footer_icon_url = self.children[1].value.strip()
                embed_data['footer_text'] = footer_text if footer_text else None
                embed_data['footer_icon_url'] = footer_icon_url if footer_icon_url else None
                await original_view._save_initial_embed_data(embed_data)
                await original_view._update_initial_embed_display(interaction)
                await interaction.followup.send("Rodapé da Mensagem Inicial atualizado!", ephemeral=True)
        
        embed_data = await self._get_initial_embed_data()
        current_footer_text = embed_data.get('footer_text', '') or ''
        current_footer_icon_url = embed_data.get('footer_icon_url', '') or ''
        await interaction.response.send_modal(InitialEmbedFooterModal(parent_view=self, current_footer_text=current_footer_text, current_footer_icon_url=current_footer_icon_url))

    @ui.button(label="Redefinir Embed", style=discord.ButtonStyle.red, row=2, custom_id="reset_initial_embed")
    async def reset_initial_embed(self, interaction: discord.Interaction, button: ui.Button):
        class ResetInitialEmbedConfirmView(ui.View):
            def __init__(self, parent_view_ref):
                super().__init__(timeout=30) # Esta view é temporária
                self.parent_view_ref = parent_view_ref

            @ui.button(label="Confirmar Redefinição", style=discord.ButtonStyle.danger, custom_id="confirm_reset_initial_embed")
            async def confirm_reset(self, interaction_confirm: discord.Interaction, button_confirm: ui.Button):
                await interaction_confirm.response.defer(ephemeral=True)
                await self.parent_view_ref._save_initial_embed_data({})
                await self.parent_view_ref._update_initial_embed_display(interaction_confirm)
                await interaction_confirm.followup.send("Embed da Mensagem Inicial redefinido para o padrão!", ephemeral=True)
                self.stop()

            @ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, custom_id="cancel_reset_initial_embed")
            async def cancel_reset(self, interaction_cancel: discord.Interaction, button_cancel: ui.Button):
                await interaction_cancel.response.defer(ephemeral=True)
                await interaction_cancel.followup.send("Redefinição da Mensagem Inicial cancelada.", ephemeral=True)
                self.stop()
            
        await interaction.response.send_message(
            "Tem certeza que deseja redefinir o embed da mensagem inicial do ticket para o padrão? Todas as personalizações serão perdidas.",
            view=ResetInitialEmbedConfirmView(self), ephemeral=True
        )

    @ui.button(label="Voltar ao Painel Principal", style=discord.ButtonStyle.secondary, row=2, custom_id="back_to_main_panel_from_initial_config")
    async def back_to_main_panel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

        for item in self.parent_view.children:
            item.disabled = False
        await self.parent_view._update_main_display(interaction)
        await interaction.followup.send("Retornando ao painel principal do Ticket.", ephemeral=True)


# Nova View Principal para o Sistema de Tickets
class TicketSystemMainView(ui.View):
    def __init__(self, bot: commands.Bot, guild_id: int):
        super().__init__(timeout=180) # Esta view é temporária para a sessão de configuração
        self.bot = bot
        self.guild_id = guild_id
        self.message = None

    async def on_timeout(self):
        if self.message:
            for item in self.children:
                item.disabled = True
            await self.message.edit(content="Sessão de configuração do sistema de tickets expirada.", view=self)

    async def _update_main_display(self, interaction: discord.Interaction):
        """Atualiza a exibição do painel principal de configurações de tickets."""
        embed = discord.Embed(
            title="Painel Principal do Sistema de Tickets",
            description="Selecione uma opção para gerenciar o sistema de tickets.",
            color=discord.Color.dark_blue() # Default color for the main config panel
        )
        embed.add_field(name="Configurações do Painel", value="Personalize a mensagem de abertura de ticket.", inline=False)
        embed.add_field(name="Logs de Tickets", value="Visualize e gerencie os registros de tickets fechados.", inline=False)
        embed.add_field(name="Mensagem Inicial do Ticket", value="Personalize o embed que aparece ao abrir um ticket.", inline=False)


        if self.message:
            await self.message.edit(embed=embed, view=self)
        else:
            if interaction.response.is_done():
                self.message = await interaction.followup.send(embed=embed, view=self, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
                self.message = await interaction.original_response()

    @ui.button(label="Configurar Painel de Tickets", style=discord.ButtonStyle.primary, row=0, custom_id="config_ticket_panel_button")
    async def configure_ticket_panel(self, interaction: discord.Interaction, button: ui.Button):
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

        panel_config_view = TicketPanelConfigView(parent_view=self, bot=self.bot, guild_id=self.guild_id)
        await interaction.response.defer(ephemeral=True)
        await panel_config_view._update_panel_display(interaction)

    @ui.button(label="Configurar Mensagem Inicial", style=discord.ButtonStyle.primary, row=1, custom_id="config_initial_message_button")
    async def configure_initial_message(self, interaction: discord.Interaction, button: ui.Button):
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

        initial_embed_config_view = TicketInitialEmbedConfigView(parent_view=self, bot=self.bot, guild_id=self.guild_id)
        await interaction.response.defer(ephemeral=True)
        await initial_embed_config_view._update_initial_embed_display(interaction)


# View para o painel principal de tickets (este é o painel que os usuários veem para abrir tickets)
class TicketPanelView(ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None) # View persistente
        self.bot = bot

    @ui.button(label="Abrir Ticket", style=discord.ButtonStyle.primary, custom_id="open_ticket_button")
    async def open_ticket(self, interaction: discord.Interaction, button: ui.Button):
        try:
            await asyncio.sleep(0.1)
            await interaction.response.defer(ephemeral=True)
        except discord.NotFound:
            logging.error(f"Unknown interaction ao deferir open_ticket para o usuário {interaction.user.id} na guild {interaction.guild_id}.")
            return

        # Fetch existing ticket from JSON
        tickets_filepath = _get_tickets_filepath(interaction.guild_id)
        all_tickets = await _load_json_file(tickets_filepath, default_data={'tickets': []})
        existing_ticket = next((ticket for ticket in all_tickets.get('tickets', []) if ticket['user_id'] == interaction.user.id and ticket['status'] == 'open'), None)

        if existing_ticket:
            channel = self.bot.get_channel(existing_ticket['channel_id'])
            if channel:
                await interaction.followup.send(f"Você já tem um ticket aberto em {channel.mention}.", ephemeral=True)
                return
            else:
                # Clean up obsolete ticket entry in JSON
                all_tickets['tickets'] = [ticket for ticket in all_tickets.get('tickets', []) if ticket.get('channel_id') != existing_ticket['channel_id']]
                await _save_json_file(tickets_filepath, all_tickets)
                logging.warning(f"Registro de ticket obsoleto para o usuário {interaction.user.id} na guild {interaction.guild_id} removido.")

        # Fetch settings from JSON
        settings_filepath = _get_settings_filepath(interaction.guild_id)
        settings = await _load_json_file(settings_filepath, default_data={})

        category_id = settings.get('category_id')
        support_role_id = settings.get('support_role_id')
        ticket_initial_embed_data = settings.get('initial_embed') # Get data directly now

        if not category_id:
            await interaction.followup.send("O sistema de tickets não está configurado (categoria não definida). Use `/ticket setcategory` primeiro.", ephemeral=True)
            return

        category = self.bot.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            await interaction.followup.send("A categoria de tickets configurada é inválida ou não existe. Por favor, reconfigure com `/ticket setcategory`.", ephemeral=True)
            return

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        if support_role_id:
            support_role = interaction.guild.get_role(support_role_id)
            if support_role:
                overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            else:
                await interaction.followup.send("O cargo de suporte configurado não foi encontrado. O ticket será criado sem permissões para o cargo.", ephemeral=True)

        try:
            ticket_channel = await category.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)
            
            # Add new ticket to JSON
            # Generate a simple ticket ID (timestamp + user ID last digits)
            timestamp_id = int(datetime.datetime.now().timestamp())
            user_id_suffix = str(interaction.user.id)[-4:]
            ticket_id = f"{timestamp_id}-{user_id_suffix}"

            new_ticket = {
                'ticket_id': ticket_id,
                'guild_id': interaction.guild_id,
                'channel_id': ticket_channel.id,
                'user_id': interaction.user.id,
                'created_at': datetime.datetime.now().isoformat(),
                'status': 'open',
                'closed_by_id': None,
                'closed_at': None
            }
            all_tickets.setdefault('tickets', []).append(new_ticket)
            await _save_json_file(tickets_filepath, all_tickets)
            logging.info(f"New ticket created: {ticket_id} for user {interaction.user.id} in guild {interaction.guild_id}.")

            ticket_embed = None
            if ticket_initial_embed_data:
                try:
                    ticket_embed = _create_embed_from_data(ticket_initial_embed_data, member=interaction.user, guild=interaction.guild)
                except Exception as e:
                    logging.error(f"Erro ao criar embed inicial do ticket para guild {interaction.guild_id} ao abrir ticket: {e}", exc_info=True)
                    ticket_embed = None
            
            if not ticket_embed:
                ticket_embed = discord.Embed(
                    title=f"Ticket de Suporte - {interaction.user.display_name}",
                    description="Por favor, descreva seu problema ou questão aqui. Um membro da equipe de suporte irá atendê-lo em breve.",
                    color=discord.Color.blue()
                )
                ticket_embed.set_footer(text=f"ID do Usuário: {interaction.user.id} | Ticket ID: {ticket_id}")


            close_view = CloseTicketView()
            await ticket_channel.send(f"{interaction.user.mention}", embed=ticket_embed, view=close_view)
            await asyncio.sleep(1) # Aumenta o atraso antes do followup
            await interaction.followup.send(f"Seu ticket foi criado em {ticket_channel.mention}!", ephemeral=True)

        except discord.Forbidden:
            await interaction.followup.send("Não tenho permissão para criar canais nesta categoria. Por favor, verifique minhas permissões e as permissões da categoria.", ephemeral=True)
        except Exception as e:
            logging.error(f"Erro ao criar ticket: {e}", exc_info=True)
            # Aumenta o atraso antes do followup de erro também
            await asyncio.sleep(1)
            await interaction.followup.send(f"Ocorreu um erro ao criar o ticket: {e}", ephemeral=True)

# View para o botão de fechar ticket dentro do canal do ticket
class CloseTicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None) # View persistente

    @ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_button")
    async def close_ticket(self, interaction: discord.Interaction, button: ui.Button):
        try:
            await asyncio.sleep(0.1)
            await interaction.response.send_message("Tem certeza que deseja fechar este ticket? Isso o deletará permanentemente.", view=CloseTicketConfirmView(), ephemeral=True)
        except discord.NotFound:
            logging.error(f"Unknown interaction ao enviar confirmação de fechar ticket para o canal {interaction.channel_id}.")
            return

# View para confirmação de fechamento de ticket
class CloseTicketConfirmView(ui.View):
    def __init__(self):
        super().__init__(timeout=60) # Esta view é temporária, não persistente


    @ui.button(label="Confirmar Fechamento", style=discord.ButtonStyle.danger, custom_id="confirm_close_ticket")
    async def confirm_close(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        await asyncio.sleep(1) # Aumenta o atraso após o deferimento antes do followup

        ticket_channel = interaction.channel
        guild_id = interaction.guild_id # Adiciona a definição de guild_id
        channel_id = ticket_channel.id

        # Find the ticket in the JSON file by channel ID
        tickets_filepath = _get_tickets_filepath(guild_id)
        all_tickets = await _load_json_file(tickets_filepath, default_data={'tickets': []})
        
        ticket_info = next((ticket for ticket in all_tickets.get('tickets', []) if ticket.get('channel_id') == channel_id and ticket.get('status') == 'open'), None)

        if not ticket_info:
            await interaction.followup.send("Este canal não é um ticket ativo ou já foi fechado.", ephemeral=True)
            return

        ticket_id = ticket_info['ticket_id']
        user_id = ticket_info['user_id'] # Keep user_id for logging/transcript

        # Fetch transcript channel ID from settings JSON
        settings_filepath = _get_settings_filepath(guild_id)
        settings = await _load_json_file(settings_filepath, default_data={})
        transcript_channel_id = settings.get('transcript_channel_id')

        try:
            await interaction.followup.send("Ticket fechado com sucesso! O canal será deletado em breve.", ephemeral=True)

            if transcript_channel_id:
                cog = interaction.client.get_cog("TicketSystem")
                if cog:
                    transcript_channel = interaction.guild.get_channel(transcript_channel_id)
                    if isinstance(transcript_channel, discord.TextChannel):
                         await cog._create_transcript(ticket_channel, transcript_channel, ticket_id)
                    else:
                         logging.warning(f"Canal de transcrição configurado para guild {guild_id} ({transcript_channel_id}) não é um canal de texto válido ou não encontrado.")
                else:
                    logging.error("Cog 'TicketSystem' não encontrado para criar transcrição.")

            await ticket_channel.delete()
            logging.info(f"Canal do ticket {channel_id} deletado com sucesso.")
            
            # Update ticket status in JSON
            for ticket in all_tickets.get('tickets', []):
                if ticket.get('ticket_id') == ticket_id:
                    ticket['status'] = 'closed'
                    ticket['closed_by_id'] = interaction.user.id
                    ticket['closed_at'] = datetime.datetime.now().isoformat()
                    break
            await _save_json_file(tickets_filepath, all_tickets)
            logging.info(f"Ticket {ticket_id} (Channel ID: {channel_id}) fechado e status atualizado no JSON.")

        except discord.NotFound:
            # If channel already deleted, just update JSON
            for ticket in all_tickets.get('tickets', []):
                if ticket.get('ticket_id') == ticket_id:
                    ticket['status'] = 'closed'
                    ticket['closed_by_id'] = interaction.user.id
                    ticket['closed_at'] = datetime.datetime.now().isoformat()
                    break
            await _save_json_file(tickets_filepath, all_tickets)
            logging.warning(f"Canal do ticket {channel_id} não encontrado (já deletado). Status do ticket {ticket_id} atualizado para 'closed' no JSON.")
            await interaction.followup.send("Ticket já estava fechado ou canal inexistente. Status atualizado no registro.", ephemeral=True)
        except discord.Forbidden:
            logging.error(f"Não tenho permissão para deletar o canal do ticket {channel_id} na guild {guild_id}.")
            await interaction.followup.send("Não tenho permissão para deletar este canal. Por favor, verifique minhas permissões.", ephemeral=True)
        except Exception as e:
            logging.error(f"Erro inesperado ao fechar o ticket {ticket_id} (Channel ID: {channel_id}): {e}", exc_info=True)
            await asyncio.sleep(1) # Adiciona um atraso antes de enviar a mensagem de erro
            await interaction.followup.send(f"Ocorreu um erro inesperado ao fechar o ticket: {e}", ephemeral=True)

    @ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, custom_id="cancel_close_ticket")
    async def cancel_close(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("Fechamento de ticket cancelado.", ephemeral=True)


class TicketSystem(commands.Cog):
    # Define o grupo de comandos de barra como um atributo de classe
    ticket_group = app_commands.Group(name="ticket", description="Comandos para gerenciar o sistema de tickets.")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Registra a TicketPanelView para persistência global.
        # Ela não recebe guild_id aqui, pois isso é para o discord.py saber como reconstruir a View.
        self.bot.add_view(TicketPanelView(bot=self.bot))
        self.bot.add_view(CloseTicketView())

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info("Views persistentes de ticket garantidas.")
        # No longer need to fetch panel message from DB, relies on discord.py's persistence

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Lida com a exclusão de mensagens, verificando se foi a mensagem do painel de tickets."""
        # Only process guild messages
        if message.guild is None:
            return

        guild_id = message.guild.id
        settings_filepath = _get_settings_filepath(guild_id)
        settings = await _load_json_file(settings_filepath, default_data={})

        # Check if the deleted message is the configured ticket panel message
        panel_channel_id = settings.get('panel_channel_id')
        panel_message_id = settings.get('panel_message_id')

        if panel_channel_id is not None and panel_message_id is not None:
            if message.channel.id == panel_channel_id and message.id == panel_message_id:
                # It's the ticket panel message, remove configuration
                del settings['panel_channel_id']
                del settings['panel_message_id']
                await _save_json_file(settings_filepath, settings)
                logger.info(f"Ticket panel message deleted in guild {guild_id}. Configuration removed from JSON.")


    async def _create_transcript(self, channel: discord.TextChannel, transcript_channel: discord.TextChannel, ticket_id: str):
        """Cria uma transcrição do canal do ticket e envia para o canal de transcrição."""
        transcript_dir = "transcripts"
        os.makedirs(transcript_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{transcript_dir}/ticket-{ticket_id}-{timestamp}.txt"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"--- Transcrição do Ticket {ticket_id} ({channel.name}) ---\n")
                # Fetch channel creation time if available, otherwise use current time as approximation
                created_at_str = channel.created_at.strftime('%Y-%m-%d %H:%M:%S') if channel.created_at else 'N/A'
                f.write(f"Aberto em: {created_at_str}\n")
                f.write(f"Fechado em: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                messages = [msg async for msg in channel.history(limit=None, oldest_first=True)]
                for msg in messages:
                    f.write(f"[{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {msg.author.display_name}: {msg.clean_content}\n")
                    for attachment in msg.attachments:
                        f.write(f"    Anexo: {attachment.url}\n")
            
            # transcript_channel is passed as an object now
            await transcript_channel.send(
                f"Transcrição do Ticket {ticket_id} ({channel.name})",
                file=discord.File(filename)
            )
            logging.info(f"Transcrição do ticket {ticket_id} enviada para o canal {transcript_channel.name}.")
            
        except Exception as e:
            logging.error(f"Erro ao criar ou enviar transcrição para o ticket {ticket_id}: {e}", exc_info=True)


    # --- Comandos de Barra para Configuração ---

    @app_commands.command(name="ticketconfig", description="Abre o painel de configuração do sistema de tickets.")
    @app_commands.default_permissions(administrator=True)
    async def ticketconfig_command(self, interaction: discord.Interaction):
        main_config_view = TicketSystemMainView(self.bot, interaction.guild_id)
        await main_config_view._update_main_display(interaction)

    @app_commands.command(name="setticketchannel", description="Define o canal onde o painel principal de tickets será enviado.")
    @app_commands.describe(channel="O canal onde o painel de tickets será enviado.")
    @app_commands.default_permissions(administrator=True)
    async def set_ticket_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        # Fetch settings from JSON
        settings_filepath = _get_settings_filepath(interaction.guild_id)
        settings = await _load_json_file(settings_filepath, default_data={})

        panel_embed_data = settings.get('panel_embed')

        panel_embed = None
        if panel_embed_data:
            try:
                panel_embed = _create_embed_from_data(panel_embed_data, guild=interaction.guild)
            except Exception as e:
                logging.error(f"Erro ao criar embed do painel para guild {interaction.guild.id} ao enviar painel: {e}", exc_info=True)
        
        if not panel_embed:
            panel_embed = discord.Embed(
                title="Sistema de Tickets",
                description="Clique no botão abaixo para abrir um novo ticket de suporte.",
                color=discord.Color.blue()
            )

        try:
            # Ao enviar a mensagem, passamos uma NOVA instância da TicketPanelView
            # que será usada para esta mensagem específica.
            # A instância global registrada em __init__ é para o discord.py saber
            # como reconstruir a view a partir de uma interação persistente.
            message = await channel.send(embed=panel_embed, view=TicketPanelView(bot=self.bot))

            # Save panel channel and message ID to JSON
            settings['panel_channel_id'] = channel.id
            settings['panel_message_id'] = message.id
            await _save_json_file(settings_filepath, settings)

            await interaction.followup.send(f"Painel de tickets enviado e configurado para {channel.mention}!", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(f"Não tenho permissão para enviar mensagens em {channel.mention}.", ephemeral=True)
        except Exception as e:
            logging.error(f"Erro ao enviar painel de tickets: {e}", exc_info=True)
            await interaction.followup.send(f"Ocorreu um erro ao enviar o painel de tickets: {e}", ephemeral=True)


    @app_commands.command(name="setticketcategory", description="Define a categoria onde os canais de ticket serão criados.")
    @app_commands.describe(category="A categoria para os canais de ticket.")
    @app_commands.default_permissions(administrator=True)
    async def set_ticket_category(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        await interaction.response.defer(ephemeral=True)
        # Save category ID to JSON
        settings_filepath = _get_settings_filepath(interaction.guild_id)
        settings = await _load_json_file(settings_filepath, default_data={})
        settings['category_id'] = category.id
        await _save_json_file(settings_filepath, settings)

        await interaction.followup.send(f"Categoria de tickets definida para **{category.name}**.", ephemeral=True)

    @app_commands.command(name="setticketrole", description="Define o cargo que terá permissão para ver e gerenciar tickets.")
    @app_commands.describe(role="O cargo de suporte para tickets.")
    @app_commands.default_permissions(administrator=True)
    async def set_ticket_role(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        # Save support role ID to JSON
        settings_filepath = _get_settings_filepath(interaction.guild_id)
        settings = await _load_json_file(settings_filepath, default_data={})
        settings['support_role_id'] = role.id
        await _save_json_file(settings_filepath, settings)

        await interaction.followup.send(f"Cargo de suporte para tickets definido para **{role.name}**.", ephemeral=True)

    @app_commands.command(name="settickettranscripts", description="Define o canal para onde as transcrições dos tickets serão enviadas.")
    @app_commands.describe(channel="O canal para transcrições de tickets.")
    @app_commands.default_permissions(administrator=True)
    async def set_ticket_transcripts_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        # Save transcript channel ID to JSON
        settings_filepath = _get_settings_filepath(interaction.guild_id)
        settings = await _load_json_file(settings_filepath, default_data={})
        settings['transcript_channel_id'] = channel.id
        await _save_json_file(settings_filepath, settings)

        await interaction.followup.send(f"Canal de transcrições de tickets definido para **{channel.mention}**.", ephemeral=True)

    @ticket_group.command(name="list", description="Lista todos os tickets abertos e fechados do servidor.")
    @app_commands.default_permissions(manage_channels=True) # Permissão para gerenciar canais é um bom padrão para ver tickets
    async def ticket_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)

        guild_id = interaction.guild_id
        tickets_filepath = _get_tickets_filepath(guild_id)
        all_tickets = await _load_json_file(tickets_filepath, default_data={'tickets': []})
        tickets = all_tickets.get('tickets', [])

        if not tickets:
            await interaction.followup.send("Não há tickets registrados neste servidor.", ephemeral=True)
            return

        open_tickets_info = []
        closed_tickets_info = []

        for ticket in tickets:
            ticket_id = ticket.get('ticket_id', 'N/A')
            user_id = ticket.get('user_id')
            channel_id = ticket.get('channel_id')
            created_at_str = ticket.get('created_at', 'N/A')
            ticket_status = ticket.get('status', 'unknown')
            closed_by_id = ticket.get('closed_by_id')
            closed_at_str = ticket.get('closed_at', 'N/A')

            user = self.bot.get_user(user_id) if user_id else f"ID: {user_id}"
            channel = self.bot.get_channel(channel_id) if channel_id else f"Canal ID: {channel_id} (deletado)"
            
            try:
                created_at_formatted = datetime.datetime.fromisoformat(created_at_str).strftime("%d/%m/%Y %H:%M:%S") if created_at_str != 'N/A' else 'N/A'
            except ValueError:
                created_at_formatted = created_at_str # Use raw string if parsing fails

            if ticket_status == 'open':
                open_tickets_info.append(
                    f"**Ticket ID:** {ticket_id}\n"
                    f"**Aberto por:** {user}\n"
                    f"**Canal:** {channel}\n"
                    f"**Aberto em:** {created_at_formatted}\n"
                )
            else: # status == 'closed'
                closed_by = self.bot.get_user(closed_by_id) if closed_by_id else f"ID: {closed_by_id}"
                try:
                    closed_at_formatted = datetime.datetime.fromisoformat(closed_at_str).strftime("%d/%m/%Y %H:%M:%S") if closed_at_str != 'N/A' else 'N/A'
                except ValueError:
                     closed_at_formatted = closed_at_str # Use raw string if parsing fails

                closed_tickets_info.append(
                    f"**Ticket ID:** {ticket_id}\n"
                    f"**Aberto por:** {user}\n"
                    f"**Fechado por:** {closed_by}\n"
                    f"**Aberto em:** {created_at_formatted}\n"
                    f"**Fechado em:** {closed_at_formatted}\n"
                )
        
        embed = discord.Embed(
            title=f"Lista de Tickets do Servidor {interaction.guild.name}",
            color=discord.Color.purple()
        )

        if open_tickets_info:
            # Join with a separator that includes newline
            open_tickets_value = "\n---\n".join(open_tickets_info)
            if len(open_tickets_value) > 1024:
                 open_tickets_value = open_tickets_value[:1020] + "..." # Truncate if too long
            embed.add_field(name="Tickets Abertos", value=open_tickets_value, inline=False)
        else:
            embed.add_field(name="Tickets Abertos", value="Nenhum ticket aberto no momento.", inline=False)

        if closed_tickets_info:
            current_closed_value = ""
            field_count = 0
            for ticket_str in closed_tickets_info:
                # Check if adding the next ticket will exceed the embed field value limit
                if len(current_closed_value) + len(ticket_str) + len("\n---\n") > 1024:
                    # Add the current accumulated value as a field and start a new one
                    embed.add_field(name=f"Tickets Fechados (Parte {field_count + 1})", value=current_closed_value, inline=False)
                    current_closed_value = ticket_str + "\n"
                    field_count += 1
                else:
                    # Add the ticket string to the current value
                    if current_closed_value:
                         current_closed_value += "\n---\n" + ticket_str + "\n"
                    else:
                         current_closed_value = ticket_str + "\n"
            
            # Add any remaining accumulated value
            if current_closed_value:
                embed.add_field(name=f"Tickets Fechados (Parte {field_count + 1})" if field_count > 0 else "Tickets Fechados", value=current_closed_value.strip(), inline=False) # Use strip to remove trailing newline
        else:
            embed.add_field(name="Tickets Fechados", value="Nenhum ticket fechado registrado.", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(TicketSystem(bot))