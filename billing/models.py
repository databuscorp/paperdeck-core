from django.db import models


class Subscription(models.Model):
    """Per-staff platform subscription (₹/staff/month). Separate from AI credits."""
    org            = models.OneToOneField('users.Organization', on_delete=models.CASCADE, related_name='subscription')
    per_staff_rate = models.IntegerField(default=100)            # ₹ per staff per month
    status         = models.CharField(max_length=20, default='active')  # active | inactive
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_subscriptions'


class Wallet(models.Model):
    """Org-level AI credit wallet, shared by all staff."""
    org        = models.OneToOneField('users.Organization', on_delete=models.CASCADE, related_name='wallet')
    balance    = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pd_wallets'


class CreditTxn(models.Model):
    """Append-only ledger of credit movements."""
    org           = models.ForeignKey('users.Organization', on_delete=models.CASCADE, related_name='credit_txns')
    delta         = models.IntegerField()                       # +purchase, -consume
    kind          = models.CharField(max_length=20)             # purchase | consume | adjust
    reason        = models.CharField(max_length=255, blank=True, default='')
    balance_after = models.IntegerField(default=0)
    expires_at    = models.DateTimeField(null=True, blank=True)  # for purchase lots (12-month validity)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pd_credit_txns'
        ordering = ['-created_at']
