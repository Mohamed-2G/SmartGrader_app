import requests
import json
import os
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ExamGrader:
    def __init__(self, deepseek_token: Optional[str] = None):
        """
        Initialize the ExamGrader with DeepSeek API token.
        
        Args:
            deepseek_token: DeepSeek API token. If not provided, will try to get from .env file.
        """
        # Try to get token from parameter first, then from .env file
        self.deepseek_token = deepseek_token or os.getenv('DEEPSEEK_API_KEY')
        
        if not self.deepseek_token:
            raise ValueError(
                "DeepSeek API token is required. "
                "Set DEEPSEEK_API_KEY in your .env file or pass deepseek_token parameter. "
                "Get your token from: https://platform.deepseek.com/"
            )
        
        # DeepSeek API configuration
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.deepseek_token}",
            "Content-Type": "application/json"
        }
        
        # Model selection for different tasks
        self.grading_model = "deepseek-reasoner"  # For complex grading tasks
        self.chat_model = "deepseek-chat"         # For simple tasks like extraction
        
        print("DeepSeek API initialized successfully!")
    
    def _load_training_guidance(self) -> Dict[str, Any]:
        """Load training dataset guidance for improved grading."""
        try:
            import json
            import os
            
            # Path to the training dataset
            dataset_path = os.path.join(os.path.dirname(__file__), 'training_grading_dataset.json')
            
            if os.path.exists(dataset_path):
                with open(dataset_path, 'r', encoding='utf-8') as f:
                    training_data = json.load(f)
                return training_data
            else:
                print("Training dataset not found, using default guidance")
                return self._get_default_guidance()
                
        except Exception as e:
            print(f"Error loading training dataset: {e}")
            return self._get_default_guidance()
    
    def _get_default_guidance(self) -> Dict[str, Any]:
        """Return default grading guidance when training dataset is unavailable."""
        return {
            "model_guidance": {
                "system_prompt": "You are a strict, fair exam grader. Grade based on accuracy, relevance, and completeness—not length or style. Return ONLY a JSON object with keys: score (number), feedback (string).",
                "grading_rules": [
                    "Grade content, not length.",
                    "Award partial credit appropriately.",
                    "Point out specific correct elements.",
                    "Point out specific missing or incorrect elements.",
                    "Avoid generic praise or vague feedback."
                ]
            }
        }
    
    def _build_enhanced_system_message(self, training_guidance: Dict[str, Any], max_points: int) -> str:
        """Build enhanced system message using training dataset guidance."""
        guidance = training_guidance.get("model_guidance", {})
        system_prompt = guidance.get("system_prompt", "You are a strict, fair exam grader.")
        grading_rules = guidance.get("grading_rules", [])
        
        # Build the enhanced system message
        message = f"""{system_prompt}

GRADING RULES:
"""
        for rule in grading_rules:
            message += f"• {rule}\n"
        
        message += f"""
OUTPUT FORMAT: Return ONLY a JSON object with:
{{"score": <0-{max_points}>, "feedback": "<specific feedback>"}}

EXAMPLES:
{{"score": 5, "feedback": "Correct. Identifies X and explains Y concisely."}}
{{"score": 2, "feedback": "Partially correct. Mentions X but misses Y and Z."}}
{{"score": 0, "feedback": "Incorrect or off-topic."}}"""
        
        return message
    
    def _build_enhanced_user_message(self, question_text: str, rubric: str, student_answer: str, max_points: int, training_guidance: Dict[str, Any]) -> str:
        """Build enhanced user message with relevant examples from training dataset."""
        # Find relevant examples from the training dataset
        relevant_examples = self._find_relevant_examples(question_text, training_guidance)
        
        message = f"""QUESTION: {question_text}
RUBRIC: {rubric}
STUDENT ANSWER: {student_answer}
MAX POINTS: {max_points}

"""
        
        # Add relevant examples if found
        if relevant_examples:
            message += "RELEVANT EXAMPLES:\n"
            for i, example in enumerate(relevant_examples[:2], 1):  # Limit to 2 examples
                message += f"""Example {i}:
Q: {example['question']}
A: {example['answer']}
Score: {example['expected_points']}/{example['max_points']}
Feedback: {example['feedback']}

"""
        
        message += "GRADE THIS ANSWER:"
        return message
    
    def _find_relevant_examples(self, question_text: str, training_guidance: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find relevant examples from training dataset based on question similarity."""
        try:
            dataset = training_guidance.get("dataset", [])
            relevant_examples = []
            
            # Simple keyword matching to find relevant examples
            question_lower = question_text.lower()
            
            for item in dataset:
                item_question = item.get("question", "").lower()
                exemplars = item.get("exemplars", [])
                
                # Check if question types match or keywords overlap
                if self._questions_are_similar(question_lower, item_question):
                    for exemplar in exemplars:
                        relevant_examples.append({
                            "question": item["question"],
                            "answer": exemplar["answer"],
                            "expected_points": exemplar["expected_points"],
                            "max_points": item["max_points"],
                            "feedback": exemplar["feedback"]
                        })
            
            return relevant_examples
            
        except Exception as e:
            print(f"Error finding relevant examples: {e}")
            return []
    
    def _questions_are_similar(self, question1: str, question2: str) -> bool:
        """Check if two questions are similar based on keywords and question type."""
        # Common question type keywords
        question_types = {
            "define": ["define", "definition", "what is", "explain"],
            "compare": ["compare", "contrast", "difference", "similar"],
            "explain": ["explain", "describe", "how", "why"],
            "solve": ["solve", "calculate", "find", "compute"],
            "list": ["list", "name", "identify", "mention"]
        }
        
        # Check for question type similarity
        for qtype, keywords in question_types.items():
            if any(keyword in question1 for keyword in keywords) and any(keyword in question2 for keyword in keywords):
                return True
        
        # Check for subject similarity (simple keyword matching)
        subjects = ["history", "math", "science", "biology", "chemistry", "physics", "english", "french", "geography", "economics"]
        for subject in subjects:
            if subject in question1 and subject in question2:
                return True
        
        return False
    
    def grade_exam(self, student_answer: str, rubric: str, max_points: int = 100, question_text: str = "") -> Dict[str, Any]:
        """
        Grade a student's answer using the DeepSeek API.
        
        Args:
            student_answer: The student's answer text
            rubric: The grading rubric or prompt
            max_points: Maximum points possible (default: 100)
            question_text: The original question text (optional)
            
        Returns:
            Dictionary containing grading results
        """
        try:
            return self._grade_with_deepseek_api(student_answer, rubric, max_points, question_text)
        except Exception as e:
            print(f"DeepSeek API failed: {e}")
            # Fallback to smart grading
            return self._smart_fallback_grading(student_answer, max_points, question_text)
    
    def _grade_with_deepseek_api(self, student_answer: str, rubric: str, max_points: int, question_text: str) -> Dict[str, Any]:
        """Grade using the DeepSeek API with training dataset guidance and resilient JSON parsing."""
        import re, json

        try:
            # Load training dataset for better grading guidance
            training_guidance = self._load_training_guidance()
            
            # Enhanced system message with training dataset guidance
            system_message = self._build_enhanced_system_message(training_guidance, max_points)
            
            # Build enhanced user message with examples
            user_message = self._build_enhanced_user_message(question_text, rubric, student_answer, max_points, training_guidance)

            payload = {
                "model": self.grading_model,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": 400,
                "temperature": 0.3,
                "top_p": 0.9
            }

            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=60)

            if response.status_code != 200:
                raise Exception(f"API request failed with {response.status_code}: {response.text}")

            result = response.json()
            choice = result.get("choices", [{}])[0]
            generated_text = choice.get("message", {}).get("content", "").strip()

            # If content is empty but there's reasoning_content, try to extract JSON from there
            if not generated_text and "reasoning_content" in choice.get("message", {}):
                reasoning = choice.get("message", {}).get("reasoning_content", "")
                import re
                match = re.search(r'\{[^}]*"score"[^}]*"feedback"[^}]*\}', reasoning, re.DOTALL)
                if match:
                    generated_text = match.group()
                    print(f"Extracted JSON from reasoning: {generated_text}")

            if not generated_text:
                raise ValueError("Empty response from DeepSeek")

            # Extract JSON safely
            match = re.search(r"\{.*\}", generated_text, re.DOTALL)
            if not match:
                raise ValueError(f"No JSON found in response: {generated_text}")

            try:
                json_response = json.loads(match.group())
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in response: {generated_text}") from e

            # Extract fields
            raw_score = json_response.get("score")
            feedback = str(json_response.get("feedback", "No feedback provided"))

            # Normalize score
            score = 0
            try:
                if isinstance(raw_score, str):
                    if "/" in raw_score:  # e.g. "4/5"
                        num, denom = raw_score.split("/")
                        score = int(float(num) / float(denom) * max_points)
                    else:  # e.g. "85.0"
                        score = int(float(raw_score))
                elif isinstance(raw_score, (int, float)):
                    score = int(raw_score)
                else:
                    raise ValueError("Unsupported score format")
            except Exception:
                score = 0  # fallback to 0 if completely unparseable

            # Clamp to valid range
            score = max(0, min(score, max_points))

            return {
                "score": score,
                "max_score": max_points,
                "feedback": feedback,
                "raw_response": generated_text,
                "method": "deepseek_api"
            }

        except Exception as e:
            print(f"Error with DeepSeek API: {e}")
            raise e
    
    def grade_with_structured_rubric(self, student_answer: str, rubric_data: Dict[str, Any], question_text: str = "") -> Dict[str, Any]:
        """
        Grade using a structured rubric format.
        
        Args:
            student_answer: The student's answer text
            rubric_data: Dictionary containing rubric criteria and weights
            question_text: The original question text (optional)
            
        Returns:
            Dictionary containing grading results
        """
        # Convert structured rubric to text format
        rubric_text = "Grading Criteria:\n"
        total_weight = 0
        
        for criterion, details in rubric_data.items():
            if isinstance(details, dict):
                weight = details.get('weight', 0)
                description = details.get('description', criterion)
                rubric_text += f"- {criterion} ({weight} points): {description}\n"
                total_weight += weight
            else:
                rubric_text += f"- {criterion}: {details}\n"
        
        return self.grade_exam(student_answer, rubric_text, total_weight, question_text)
    
    def grade_with_local_model(self, student_answer: str, rubric: str, max_points: int = 100, question_text: str = "") -> Dict[str, Any]:
        """
        Grade using the DeepSeek API with smart fallback.
        
        Args:
            student_answer: The student's answer text
            rubric: The grading rubric or prompt
            max_points: Maximum points possible (default: 100)
            question_text: The original question text (optional)
            
        Returns:
            Dictionary containing grading results
        """
        try:
            # Try the DeepSeek API first
            result = self.grade_exam(student_answer, rubric, max_points, question_text)
            if not result.get('error'):
                return result
        except Exception as e:
            print(f"DeepSeek API failed: {e}")
        
        # Fallback to smart grading based on answer analysis
        return self._smart_fallback_grading(student_answer, max_points, question_text)
    
    def _smart_fallback_grading(self, student_answer: str, max_points: int, question_text: str = "") -> Dict[str, Any]:
        """
        Smarter fallback grading when AI models are not available.
        Combines length/quality heuristics with keyword coverage from the question.
        """
        import re
        from collections import Counter

        # Clean student answer
        answer_clean = student_answer.strip()
        word_count = len(answer_clean.split()) if answer_clean else 0

        # === Keyword Extraction from Question ===
        stopwords = {"the","and","or","is","a","an","of","to","in","on","for","with","by","at","from","what","how","when","who","why"}
        question_words = [w.lower() for w in re.findall(r"\w+", question_text) if w.lower() not in stopwords]
        unique_keywords = list(set(question_words))
        answer_words = [w.lower() for w in re.findall(r"\w+", student_answer)]
        missing_keywords = [kw for kw in unique_keywords if kw not in answer_words]
        
        # Count substantial words (4+ characters) for analysis
        substantial_words = len(re.findall(r'\b\w{4,}\b', student_answer))

        # === Base Scoring by Length ===
        if word_count == 0:
            score = 0
            feedback = "No answer provided. Please attempt to answer the question."
        elif word_count < 5:
            score = int(max_points * 0.1)
            feedback = "Your answer is extremely brief. Please provide more detail."
        elif word_count < 15:
            score = int(max_points * 0.3)
            feedback = "Your answer shows some understanding but needs more depth."
        elif word_count < 30:
            score = int(max_points * 0.5)
            feedback = "Decent attempt. Add more detail and clarity for a stronger response."
        elif word_count < 60:
            score = int(max_points * 0.75)
            feedback = "Good answer with reasonable detail. Nice work!"
        else:
            score = int(max_points * 0.9)
            feedback = "Very strong and detailed answer. Well done!"

        # === Adjust Score Based on Keyword Coverage ===
        if unique_keywords:
            coverage = (len(unique_keywords) - len(missing_keywords)) / len(unique_keywords)
            score = min(max_points, int(score * (0.6 + coverage * 0.4)))  # weight coverage into final score

        # === Feedback on Missing Keywords ===
        if missing_keywords:
            feedback += f" However, you did not mention key concept(s): {', '.join(missing_keywords[:3])}."
        else:
            feedback += " You covered the main concepts well."

        # === Encourage Improvement ===
        if score < max_points * 0.4:
            feedback += " Keep practicing and try to connect your answer more closely to the question."
        elif score < max_points * 0.7:
            feedback += " You're making progress. Add more examples and explanations to strengthen your answer."
        else:
            feedback += " Strong performance shows good understanding."

        return {
            "score": int(score),
            "max_score": max_points,
            "feedback": feedback,
            "method": "smart_fallback",
            "analysis": {
                "word_count": word_count,
                "keywords_expected": unique_keywords,
                "keywords_missing": missing_keywords,
                "substantial_words": substantial_words
            }
        }

    def debug_deepseek_response(self, student_answer: str, rubric: str, max_points: int = 100, question_text: str = "") -> Dict[str, Any]:
        """
        Debug method to test DeepSeek API responses and see what's being returned.
        Useful for troubleshooting parsing issues.
        """
        try:
            # Create the same prompt as the main grading method
            system_message = f"""You are a strict exam grader. Grade the answer according to the rubric. 
Respond ONLY in JSON format with keys 'score' and 'feedback'.
- score: must be a number between 0 and {max_points}
- feedback: must be a string with specific details about what is correct and what is missing
- Do not include any text outside the JSON object
- Do not add explanations, just the JSON"""

            user_message = f"""Question: {question_text}
Rubric: {rubric}
Student Answer: {student_answer}
Max Points: {max_points}

Respond with ONLY a JSON object like this:
{{"score": 85, "feedback": "Good understanding of the topic. Correctly identifies key concepts but missing specific examples."}}"""

            payload = {
                "model": self.grading_model,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": 300,
                "temperature": 0.3,
                "top_p": 0.9
            }
            
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=60)
            
            debug_info = {
                "status_code": response.status_code,
                "raw_response": response.text if response.status_code != 200 else None,
                "payload": payload,
                "parsing_attempts": []
            }
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result['choices'][0]['message']['content'].strip()
                debug_info["generated_text"] = generated_text
                
                # Try different parsing methods
                import re
                
                # Method 1: Direct JSON parsing
                try:
                    json_response = json.loads(generated_text)
                    debug_info["parsing_attempts"].append({
                        "method": "direct_json",
                        "success": True,
                        "result": json_response
                    })
                except json.JSONDecodeError as e:
                    debug_info["parsing_attempts"].append({
                        "method": "direct_json",
                        "success": False,
                        "error": str(e)
                    })
                
                # Method 2: Regex extraction
                match = re.search(r'\{.*\}', generated_text, re.DOTALL)
                if match:
                    try:
                        json_response = json.loads(match.group())
                        debug_info["parsing_attempts"].append({
                            "method": "regex_extraction",
                            "success": True,
                            "result": json_response,
                            "extracted_text": match.group()
                        })
                    except json.JSONDecodeError as e:
                        debug_info["parsing_attempts"].append({
                            "method": "regex_extraction",
                            "success": False,
                            "error": str(e),
                            "extracted_text": match.group()
                        })
                else:
                    debug_info["parsing_attempts"].append({
                        "method": "regex_extraction",
                        "success": False,
                        "error": "No JSON object found"
                    })
                
                # Method 3: Look for score and feedback patterns
                score_match = re.search(r'["\']?score["\']?\s*:\s*(\d+)', generated_text, re.IGNORECASE)
                feedback_match = re.search(r'["\']?feedback["\']?\s*:\s*["\']([^"\']+)["\']', generated_text, re.IGNORECASE)
                
                if score_match and feedback_match:
                    debug_info["parsing_attempts"].append({
                        "method": "pattern_matching",
                        "success": True,
                        "result": {
                            "score": int(score_match.group(1)),
                            "feedback": feedback_match.group(1)
                        }
                    })
                else:
                    debug_info["parsing_attempts"].append({
                        "method": "pattern_matching",
                        "success": False,
                        "error": f"Score match: {bool(score_match)}, Feedback match: {bool(feedback_match)}"
                    })
                
            else:
                debug_info["error"] = f"API request failed with status {response.status_code}"
            
            return debug_info
            
        except Exception as e:
            return {
                "error": str(e),
                "exception_type": type(e).__name__
            }

    def test_api_connection(self) -> Dict[str, Any]:
        """
        Test the DeepSeek API connection and validate the token.
        Returns connection status and available models.
        """
        try:
            # Simple test request
            test_payload = {
                "model": self.grading_model,
                "messages": [
                    {"role": "user", "content": "Hello, please respond with 'API connection successful'."}
                ],
                "max_tokens": 50,
                "temperature": 0.1
            }
            
            response = requests.post(self.api_url, headers=self.headers, json=test_payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result['choices'][0]['message']['content'].strip()
                
                return {
                    "status": "success",
                    "message": "API connection successful",
                    "response": generated_text,
                    "model": self.grading_model,
                    "status_code": response.status_code
                }
            elif response.status_code == 401:
                return {
                    "status": "error",
                    "message": "Invalid API token",
                    "status_code": response.status_code,
                    "response": response.text
                }
            elif response.status_code == 404:
                return {
                    "status": "error",
                    "message": "Model not found or API endpoint incorrect",
                    "status_code": response.status_code,
                    "response": response.text
                }
            else:
                return {
                    "status": "error",
                    "message": f"API request failed with status {response.status_code}",
                    "status_code": response.status_code,
                    "response": response.text
                }
                
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "message": "API request timed out",
                "status_code": None
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "message": "Connection error - check your internet connection",
                "status_code": None
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "status_code": None
            }
