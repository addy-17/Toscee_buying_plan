"""
LLM Generator
==============
Generates natural language "Complete the Look" messages using Gemma/Llama.
Provides a template-based fallback when LLM is not available.
"""
import logging
from typing import List, Dict, Optional
from utils.config import LLM_MODEL_NAME, USE_LOCAL_LLM

logger = logging.getLogger(__name__)


class LLMGenerator:
    """
    Generate fashion-savvy "Complete the Look" messages.
    
    Uses Gemma/Llama when available, with template-based fallback.
    """

    def __init__(self, model_name: str = LLM_MODEL_NAME, use_local: bool = USE_LOCAL_LLM):
        self.model_name = model_name
        self.use_local = use_local
        self.model = None
        self.tokenizer = None

        if use_local:
            self._load_model()

    def _load_model(self):
        """Load LLM model locally."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            logger.info(f"Loading LLM: {self.model_name}...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map="auto",
                torch_dtype="auto",
            )
            logger.info("LLM loaded successfully.")
        except Exception as e:
            logger.warning(f"Failed to load LLM: {e}. Using template fallback.")
            self.use_local = False

    def generate(self, prompt: str, max_length: int = 150) -> str:
        """Generate text using the LLM."""
        if not self.use_local or self.model is None:
            return self._template_fallback(prompt)

        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_length,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
            )
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Remove the input prompt from the response
            response = response[len(prompt):].strip()
            return response
        except Exception as e:
            logger.warning(f"LLM generation failed: {e}")
            return self._template_fallback(prompt)

    def generate_complete_look_message(
        self,
        detected_products: List[Dict],
        suggestions: List[Dict],
    ) -> str:
        """
        Generate a "Complete the look" style suggestion message.
        
        Args:
            detected_products: List of detected product dicts with "label" key
            suggestions: List of suggested products
            
        Returns:
            Natural language suggestion message
        """
        if not detected_products:
            return "Upload a photo of a product to get style suggestions!"

        # Build detected items description
        detected_items = []
        for dp in detected_products:
            label = dp.get("label", "item")
            detected_items.append(label.lower())
        
        detected_text = " and ".join(detected_items)
        primary_item = detected_items[0] if detected_items else "item"

        if not suggestions:
            # No suggestions found — suggest browsing
            return (
                f"I can see you're looking at a **{primary_item}**!\n\n"
                f"While I couldn't find exact matching items in this collection, "
                f"try browsing our catalog for complementary pieces like "
                f"**earrings, bags, or fragrances** to complete your look."
            )

        # Categorize suggestions
        by_category = {}
        for s in suggestions:
            cat = s.get("category", "Accessories")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(s)

        # Build suggestion text
        suggestion_lines = []
        for category, items in by_category.items():
            item_names = []
            for item in items[:2]:  # Max 2 per category
                name = item.get("product_name", "")
                brand = item.get("brand", "")
                price = item.get("price", 0)
                if name:
                    short_name = name[:25]
                    if price:
                        item_names.append(f"**{short_name}** (₹{price:,.0f})")
                    else:
                        item_names.append(f"**{short_name}**")
            
            if item_names:
                suggestion_lines.append(f"- **{category}**: {', '.join(item_names)}")

        suggestions_text = "\n".join(suggestion_lines)

        # Use LLM for more sophisticated message if available
        if self.use_local:
            prompt = (
                f"A customer is looking at a {detected_text}. "
                f"Suggest these items to complete their look: {suggestions_text}. "
                f"Write a short, friendly 'Complete the look' message in 1-2 sentences."
            )
            llm_message = self.generate(prompt)
            if llm_message:
                return llm_message

        # Template fallback
        total_value = sum(s.get("price", 0) for s in suggestions[:4])
        
        message = (
            f"✨ **Complete your {primary_item} look!**\n\n"
            f"Based on your {detected_text}, we recommend:\n\n"
            f"{suggestions_text}\n\n"
        )

        if total_value > 0:
            message += f"💎 **Total for suggested pieces**: ₹{total_value:,.0f}\n\n"

        message += (
            f"🛍️ *Click any item to view details or add to your buying plan.*\n\n"
            f"💡 *Tip: These items work together because they complement "
            f"the style and occasion of your {primary_item}.*"
        )

        return message

    def _template_fallback(self, prompt: str) -> str:
        """Fallback when LLM is unavailable."""
        return ""

    def generate_brand_description(self, brand_name: str, product_count: int, 
                                    categories: List[str]) -> str:
        """Generate a description for a brand."""
        if self.use_local:
            prompt = (
                f"Write a one-sentence description for {brand_name}, "
                f"a fashion brand with {product_count} products "
                f"in categories: {', '.join(categories)}."
            )
            return self.generate(prompt, max_length=80)
        
        # Template fallback
        cats = ", ".join(categories[:3])
        return (
            f"**{brand_name}** offers {product_count} products "
            f"across {cats} and more. "
            f"Perfect for adding variety to your buying plan."
        )