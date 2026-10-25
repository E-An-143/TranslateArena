"""Shared labels and prompt instructions for translation styles."""

TRANSLATION_STYLES = {
    "general": ("通用", "Match the source text's register and use clear, natural target-language expression."),
    "academic": ("学术", "Use an academic style with precise terminology, formal phrasing and restrained claims. "
                 "Do not add citations, evidence or technical detail absent from the source."),
    "dialogue": ("对话", "Use a conversational style with natural spoken phrasing and an easy rhythm. "
                "Preserve each speaker's intention; do not invent dialogue or change who is speaking."),
    "business": ("商务", "Use a professional business style with clear, courteous and direct wording. "
                 "Preserve the exact commitments and meaning; do not add promises or promotional claims."),
    "literary": ("文学", "Use literary phrasing that carries the source's imagery, rhythm and narrative voice. "
                 "Do not add images, embellishments or interpretations absent from the source."),
    "news": ("新闻", "Use a news-reporting style with concise, factual and neutral wording. "
             "Preserve attribution and degrees of certainty; do not invent headlines or background information."),
}
