from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class ContactCommand:
    name: str
    email: str
    subject: str
    message: str
    company_website: str = ""
    form_started_at: str = ""


@dataclass
class ContactForm:
    command: ContactCommand
    errors: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, str]) -> "ContactForm":
        return cls(
            ContactCommand(
                name=data.get("name", "").strip(),
                email=data.get("email", "").strip(),
                subject=data.get("subject", "").strip(),
                message=data.get("message", "").strip(),
                company_website=data.get("company_website", "").strip(),
                form_started_at=data.get("form_started_at", "").strip(),
            )
        )

    def validate(self) -> bool:
        if not (2 <= len(self.command.name) <= 160):
            self.add_error("name", "Name is required")
        if not EMAIL_PATTERN.match(self.command.email):
            self.add_error("email", "Valid reply email is required")
        if not (1 <= len(self.command.subject) <= 180):
            self.add_error("subject", "Subject is required")
        if not (10 <= len(self.command.message) <= 5000):
            self.add_error("message", "Message must be between 10 and 5000 characters")
        return not self.errors

    def add_error(self, field_name: str, message: str) -> None:
        self.errors.setdefault(field_name, []).append(message)
