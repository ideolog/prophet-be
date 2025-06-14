from django.db import models
from django.utils.timezone import now

class UserAccount(models.Model):
    wallet_address = models.CharField(max_length=255, unique=True, help_text="Solana wallet address")
    verification_status = models.ForeignKey(
        'narratives.VerificationStatus',
        on_delete=models.PROTECT,
        related_name="users",
        help_text="Verification status of the user"
    )
    balance = models.DecimalField(
        max_digits=20, decimal_places=8, default=1000.0,
        help_text="User's balance in SOL tokens"
    )
    created_at = models.DateTimeField(default=now, help_text="Account creation timestamp")
    updated_at = models.DateTimeField(auto_now=True, help_text="Last update timestamp")

    def __str__(self):
        return f"{self.wallet_address} - {self.balance} SOL"
