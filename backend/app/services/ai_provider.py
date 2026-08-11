import base64
from typing import Protocol, runtime_checkable

from openai import OpenAI, OpenAIError

from app.schemas.document_processing import InvoiceExtraction
from app.schemas.insights import ExecutiveSummaryResponse


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


class OpenAIInvoiceExtractionProvider:
    """Extract invoice fields from validated PDFs and images using OpenAI."""

    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        if not api_key:
            raise AIProviderNotConfiguredError(
                "OPENAI_API_KEY must be configured for invoice extraction"
            )
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def extract_invoice(
        self,
        document_content: bytes,
        content_type: str,
    ) -> InvoiceExtraction:
        if content_type not in {
            "application/pdf",
            "image/jpeg",
            "image/png",
        }:
            raise AIProviderProcessingError(
                "OpenAI invoice extraction only supports PDF, JPEG, and PNG files"
            )

        encoded_document = base64.b64encode(document_content).decode("ascii")
        if content_type == "application/pdf":
            document_input = {
                "type": "input_file",
                "filename": "invoice.pdf",
                "file_data": "data:application/pdf;base64," + encoded_document,
            }
        else:
            document_input = {
                "type": "input_image",
                "image_url": "data:" + content_type + ";base64," + encoded_document,
                "detail": "high",
            }

        try:
            response = self._client.responses.parse(
                model=self._model,
                store=False,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "Extract invoice fields from this document. "
                                    "Return only values supported by the schema. "
                                    "Leave uncertain fields empty; do not invent values."
                                ),
                            },
                            document_input,
                        ],
                    }
                ],
                text_format=InvoiceExtraction,
            )
        except OpenAIError as exc:
            raise AIProviderProcessingError(
                "OpenAI invoice extraction request failed"
            ) from exc

        extraction = response.output_parsed
        if extraction is None:
            raise AIProviderProcessingError(
                "OpenAI did not return a structured invoice extraction"
            )
        return extraction

    def generate_executive_summary(
        self,
        insight_snapshot: str,
    ) -> ExecutiveSummaryResponse:
        try:
            response = self._client.responses.parse(
                model=self._model,
                store=False,
                input=(
                    "Create a concise executive financial briefing from this "
                    "aggregated data only. Do not invent facts.\n\n"
                    + insight_snapshot
                ),
                text_format=ExecutiveSummaryResponse,
            )
        except OpenAIError as exc:
            raise AIProviderProcessingError(
                "OpenAI executive-summary request failed"
            ) from exc
        if response.output_parsed is None:
            raise AIProviderProcessingError(
                "OpenAI did not return a structured executive summary"
            )
        return response.output_parsed
