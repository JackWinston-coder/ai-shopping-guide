from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    reason: str = ""


class OutputValidator:
    def validate_product_references(self, output: str, product_cards: list[dict]) -> ValidationResult:
        if not output.strip() or not product_cards:
            return ValidationResult(valid=True)

        allowed_ids = {str(product.get("product_id", "")) for product in product_cards}

        known_product_tokens = ("p_beauty_", "p_digital_", "p_clothes_", "p_food_")
        for token in known_product_tokens:
            if token in output:
                mentioned_ids = [
                    part.strip("，。,.、；;：:()（）[]【】")
                    for part in output.split()
                    if token in part
                ]
                for mentioned_id in mentioned_ids:
                    if mentioned_id not in allowed_ids:
                        return ValidationResult(valid=False, reason=f"回复提到了未返回的商品ID：{mentioned_id}")

        return ValidationResult(valid=True)
