from django.db import models
from decimal import Decimal
from narratives.models.claims import Claim
from narratives.models.users import UserAccount


class Market(models.Model):
    claim = models.OneToOneField(Claim, on_delete=models.CASCADE, related_name="market")
    creator = models.CharField(max_length=255, help_text="Wallet address of the market creator.")
    created_at = models.DateTimeField(auto_now_add=True)

    contract_address = models.CharField(max_length=255, blank=True, null=True, help_text="Future Smart Contract address.")
    transaction_hash = models.CharField(max_length=255, blank=True, null=True, help_text="Blockchain transaction hash.")

    true_shares_remaining = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal('1000000000.0'))
    false_shares_remaining = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal('1000000000.0'))

    def current_price_for_side(self, side: str) -> Decimal:
        base_price = Decimal("0.0001")
        slope = Decimal("0.0000001")
        initial_shares = Decimal("1000000000.0")

        current_remaining = self.true_shares_remaining if side == "TRUE" else self.false_shares_remaining
        x = initial_shares - current_remaining
        price = base_price + (slope * x)
        return price.quantize(Decimal("0.00000001"))

    def cost_to_buy_linear(self, side: str, shares_wanted: Decimal) -> Decimal:
        base_price = Decimal("0.0001")
        slope = Decimal("0.0000001")
        initial_shares = Decimal("1000000000.0")

        current_remaining = self.true_shares_remaining if side == "TRUE" else self.false_shares_remaining
        x = initial_shares - current_remaining
        delta = shares_wanted

        cost = base_price * delta + (slope / Decimal("2")) * ((x + delta) ** 2 - x ** 2)
        return cost.quantize(Decimal("0.00000001"))

    def __str__(self):
        return f"Market for {self.claim.text[:50]} by {self.creator}"


class MarketPosition(models.Model):
    SIDE_CHOICES = [("TRUE", "True"), ("FALSE", "False")]

    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE)
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    side = models.CharField(max_length=5, choices=SIDE_CHOICES)

    shares = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal('0.0'))
    cost_basis = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal('0.0'))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'market'], name='unique_user_market')
        ]

    def __str__(self):
        return f"{self.user.wallet_address} - {self.side} - {self.shares} shares"
