from typing import Protocol, runtime_checkable

from app.schemas.document_processing import InvoiceExtraction


class AIProviderNotConfiguredError(RuntimeError):
    pass


class AIProviderProcessingError(RuntimeError):
    pass


@runtime_checkable
class InvoiceExtractionProvider(Protocol):
    name: str

    def extract_invoice(
        self,
        document_content: bytes,
        content_type: str,
    ) -> InvoiceExtraction:
        """Extract validated invoice data from one supported document."""


class UnconfiguredInvoiceExtractionProvider:
    name = "unconfigured"

    def extract_invoice(
        self,
        document_content: bytes,
        content_type: str,
    ) -> InvoiceExtraction:
        raise AIProviderNotConfiguredError(
            "No AI invoice-extraction provider has been configured"
        )
