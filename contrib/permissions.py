BILLING = "__billing__"
BOT = "__bot__"
CROSS = "__cross__"
EVENT = "__event__"
MANAGER = "__manager__"
OPERATOR = "__operator__"
PUBLIC = "__public__"
SUPERUSER = "__superuser__"

ADMIN = [MANAGER, SUPERUSER]
USER = [OPERATOR, *ADMIN]
