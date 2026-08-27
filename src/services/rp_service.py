"""Roleplay (RP) actions parsing and processing service."""

import re
from typing import Any

from src.infrastructure.constants.levels import ALL_COUPLE_COMMANDS, VALID_COMMANDS
from src.infrastructure.constants.names import USERS_MAP
from src.infrastructure.db.repository import (
    get_first_name_by_username,
    update_user_cache,
)
from src.infrastructure.utils.declension import decline_name
from src.infrastructure.utils.formatting import create_user_link, escape_html


class RPService:
    """Service handling parsing, grammatical declension, and formatting of RP actions."""

    @staticmethod
    async def process_rp_action(
        message_text: str,
        from_user: Any,
        reply_user: Any = None,
        entities: Any = None,
        bot_username: str | None = None,
    ) -> str | None:
        """Parse message for custom roleplay action and return formatted response."""
        if not (message_text.startswith("/") or message_text.startswith("!")):
            return None

        sender_id = from_user.id if from_user else None
        sender_username = from_user.username.lower() if from_user and from_user.username else ""

        # Resolve sender display name
        if sender_username and sender_username in USERS_MAP:
            sender_name = USERS_MAP[sender_username]
        else:
            sender_name = (
                from_user.first_name or from_user.username or "Користувач"
                if from_user
                else "Користувач"
            )

        # Update cache for sender
        if from_user and from_user.username:
            await update_user_cache(from_user.username, sender_name, sender_id)

        target_user_id: int | None = None
        target_display_name: str | None = None
        action = ""
        rest_text = ""

        # Case A: Action via Reply to message
        if reply_user:
            target_user_id = reply_user.id
            reply_uname = (reply_user.username or "").lower()
            if reply_uname in USERS_MAP:
                target_display_name = USERS_MAP[reply_uname]
            else:
                target_display_name = reply_user.first_name or reply_user.username or "Користувач"

            match_reply = re.match(r"^[/\!](\S+)\s*(.*)$", message_text, re.DOTALL)
            if match_reply:
                action = match_reply.group(1).strip()
                rest_text = match_reply.group(2).strip()

        # Case B: Action via @mention or entities
        elif "@" in message_text:
            pattern = r"^[/\!]([^@]+?)\s*@([^\s]+)(.*)$"
            match_mention = re.match(pattern, message_text, re.DOTALL)

            if match_mention:
                action = match_mention.group(1).strip()
                raw_target = match_mention.group(2).strip().lstrip("@")
                rest_text = match_mention.group(3).strip() if match_mention.group(3) else ""

                # Check text_mention in entities
                if entities:
                    for entity in entities:
                        if entity.type == "text_mention" and entity.user:
                            target_user_id = entity.user.id
                            target_display_name = entity.user.first_name or entity.user.username
                            break

                # Static USERS_MAP
                if not target_display_name and raw_target.lower() in USERS_MAP:
                    target_display_name = USERS_MAP[raw_target.lower()]

                # Dynamic cache
                if not target_user_id or not target_display_name:
                    cached_name, cached_id = await get_first_name_by_username(raw_target)
                    if cached_name and not target_display_name:
                        target_display_name = cached_name
                    if cached_id and not target_user_id:
                        target_user_id = cached_id

                if not target_display_name:
                    target_display_name = raw_target

        # Case C: Standalone action without recipient
        else:
            action_match = re.match(r"^[/\!](.+)$", message_text)
            if action_match:
                action_text = action_match.group(1).strip()
                first_word = action_text.split()[0] if action_text.split() else action_text
                if first_word not in ALL_COUPLE_COMMANDS and first_word not in VALID_COMMANDS:
                    sender_link = create_user_link(sender_id, sender_name)
                    return f"✨ {sender_link} {escape_html(action_text)}"
            return None

        if not action or action in ALL_COUPLE_COMMANDS:
            return None

        # Bot immunity check
        if (
            bot_username
            and target_display_name
            and target_display_name.lower() == bot_username.lower()
        ):
            return "🤖 На мені не можна виконувати дії!"

        # Grammatical declension
        target_declined = decline_name(target_display_name) if target_display_name else ""

        sender_link = create_user_link(sender_id, sender_name)
        target_link = create_user_link(target_user_id, target_declined)

        response = f"✨ {sender_link} {escape_html(action)} {target_link}"
        if rest_text:
            response += f" {escape_html(rest_text)}"

        return response
