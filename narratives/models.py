from django.db import models
from django.utils.text import slugify
from django.utils.timezone import now
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.crypto import get_random_string
from decimal import Decimal


### USER & VERIFICATION

class UserAccount(models.Model):
    wallet_address = models.CharField(max_length=255, unique=True, help_text="Solana wallet address")
    verification_status = models.ForeignKey(
        'VerificationStatus',
        on_delete=models.PROTECT,
        related_name="users",
        help_text="Verification status of the user"
    )
    balance = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal('1000.0'))
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.wallet_address} - {self.balance} SOL"


class VerificationStatus(models.Model):
    STATUS_CHOICES = [
        ('unverified', 'Unverified'),
        ('pending_ai_review', 'Pending AI Review'),
        ('market_created', 'Market Created'),
        ('ai_reviewed', 'AI Reviewed'),
        ('user_approved', 'User Approved'),
        ('ai_variants_generated', 'AI Variants Generated'),
        ('validator_review', 'Validator Review'),
        ('approved_for_blockchain', 'Approved for Blockchain'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
    ]

    name = models.CharField(max_length=50, choices=STATUS_CHOICES, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Verification Status"
        verbose_name_plural = "Verification Statuses"

    def __str__(self):
        return self.get_name_display()


### CLAIMS

class Claim(models.Model):
    text = models.TextField(unique=True, help_text="The claim text.")
    slug = models.SlugField(unique=True, blank=True, max_length=150)
    verification_status = models.ForeignKey('VerificationStatus', on_delete=models.PROTECT, related_name="claims")
    status_description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    author = models.CharField(max_length=255, help_text="Wallet address or AI model")
    parent_claim = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name="ai_variants")
    generated_by_ai = models.BooleanField(default=False)
    ai_model = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.text[:50]

@receiver(pre_save, sender=Claim)
def create_claim_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        base_slug = slugify(instance.text)[:150]
        unique_slug = base_slug
        while Claim.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{get_random_string(5)}"
        instance.slug = unique_slug


### SCHOOLS OF THOUGHT & VALUES

class SchoolOfThoughtType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class SchoolOfThought(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    type = models.ForeignKey(SchoolOfThoughtType, on_delete=models.CASCADE, related_name='schools_of_thought')
    parent_school = models.ForeignKey('self', blank=True, null=True, on_delete=models.CASCADE, related_name='sub_schools')
    slug = models.SlugField(unique=True, blank=True, max_length=150)

    def __str__(self):
        return self.name

@receiver(pre_save, sender=SchoolOfThought)
def create_sot_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        base_slug = slugify(instance.name)[:150]
        unique_slug = base_slug
        while SchoolOfThought.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{get_random_string(5)}"
        instance.slug = unique_slug


class Value(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True, max_length=150)

    def __str__(self):
        return self.name

@receiver(pre_save, sender=Value)
def create_value_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        base_slug = slugify(instance.name)[:150]
        unique_slug = base_slug
        while Value.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{get_random_string(5)}"
        instance.slug = unique_slug


### EPOCHS

class Epoch(models.Model):
    title = models.CharField(max_length=255, unique=True, help_text="E.g., Biden Presidency, Cold War, etc.")
    slug = models.SlugField(unique=True, blank=True, max_length=150)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        if self.end_date:
            return f"{self.title} ({self.start_date} - {self.end_date})"
        return f"{self.title} (Starting {self.start_date})"

@receiver(pre_save, sender=Epoch)
def create_epoch_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        base_slug = slugify(instance.title)[:150]
        unique_slug = base_slug
        while Epoch.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{get_random_string(5)}"
        instance.slug = unique_slug


### MARKETS

class Market(models.Model):
    claim = models.OneToOneField(Claim, on_delete=models.CASCADE, related_name="market")
    creator = models.CharField(max_length=255, help_text="Wallet address of the market creator.")
    created_at = models.DateTimeField(auto_now_add=True)

    contract_address = models.CharField(max_length=255, blank=True, null=True)
    transaction_hash = models.CharField(max_length=255, blank=True, null=True)

    true_shares_remaining = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal('1000000000.0'))
    false_shares_remaining = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal('1000000000.0'))

    def current_price_for_side(self, side: str) -> Decimal:
        base_price = Decimal("0.0001")
        slope = Decimal("0.0000001")
        initial_shares = Decimal("1000000000.0")
        current_remaining = self.true_shares_remaining if side == "TRUE" else self.false_shares_remaining
        sold_shares = initial_shares - current_remaining
        return (base_price + (slope * sold_shares)).quantize(Decimal("0.00000001"))

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
        constraints = [models.UniqueConstraint(fields=['user', 'market'], name='unique_user_market')]

    def __str__(self):
        return f"{self.user.wallet_address} - {self.side} - {self.shares} shares"
