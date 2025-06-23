from django.core.management.base import BaseCommand
from narratives.models import VerificationStatus

class Command(BaseCommand):
    help = "Add predefined verification statuses to the database."

    def handle(self, *args, **options):
        statuses = [
            {'name': 'unverified', 'description': 'Default status when claim is first submitted.'},
            {'name': 'pending_ai_review', 'description': 'Claim is undergoing checks by AI.'},
            {'name': 'ai_reviewed', 'description': 'AI has reviewed and approved the claim.'},
            {'name': 'user_approved', 'description': 'User has selected and approved a claim variant.'},
            {'name': 'validator_review', 'description': 'Validators are reviewing the claim.'},
            {'name': 'approved_for_blockchain', 'description': 'Claim is approved and ready for the blockchain.'},
            {'name': 'published', 'description': 'Claim is live on the blockchain.'},
            {'name': 'rejected', 'description': 'Claim has been rejected and will not proceed.'},
        ]

        for status in statuses:
            obj, created = VerificationStatus.objects.get_or_create(
                name=status['name'],
                defaults={'description': status['description']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Added status: {status['name']}"))
            else:
                self.stdout.write(self.style.WARNING(f"Status already exists: {status['name']}"))