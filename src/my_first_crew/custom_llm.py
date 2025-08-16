from crewai import BaseLLM
from typing import Any, Dict, List, Optional, Union
from my_first_crew.tools.custom_tool import CrawlWebsiteTool, FlexibleSerperDevTool
from google import genai
from google.genai import types
import time
import json
import hashlib
import re
import logging

logging.basicConfig(level=logging.INFO)

class Gemini(BaseLLM):
    def __init__(self, model: str, api_key: str, temperature: Optional[float] = None):
        super().__init__(model=model, temperature=temperature)
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)

    def call(
        self,
        messages: Union[str, List[Dict[str, Any]]],
        tools: Optional[List[Any]] = None,
        callbacks: Optional[List[Any]] = None,
        available_functions: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        if not tools or not available_functions:
            extracted_tools, extracted_functions = self._extract_tools_from_system_message(messages)
            tools = tools or extracted_tools
            available_functions = available_functions or extracted_functions
        contents, system_instruction = self._to_contents(messages)
        config = self._to_config(tools, available_functions, system_instruction)

        last_exc: Optional[Exception] = None
        for _ in range(2):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )

                # Validate response
                if not response or not hasattr(response, 'candidates') or not response.candidates:
                    logging.warning("Gemini returned empty response.")
                    return "I apologize, but I couldn't generate a response. Please try again."

                parsed_response = self._parse_response(response, messages)
                return str(parsed_response)

            except Exception as exc:
                last_exc = exc
                logging.warning(f"Gemini call failed: {exc}, retrying...")
                time.sleep(0.7)

        raise last_exc

    def _is_react_mode(self, messages):
        system_msg = next((m['content'] for m in messages if m.get('role') == 'system'), "")
        return any(k in system_msg for k in ["Action:", "Observation:", "Thought:"])

    def _to_contents(
        self,
        messages: Union[str, List[Dict[str, Any]]]
    ) -> tuple[list[types.Content], Optional[str]]:
        if isinstance(messages, str):
            return [types.Content(role="user", parts=[types.Part(text=messages)])], None

        contents: list[types.Content] = []
        system_instruction: Optional[str] = None

        for msg in messages:
            role = msg.get("role", "user")
            text = msg.get("content", "")
            if not isinstance(text, str):
                text = str(text)

            if role == "system":
                clean_text = re.sub(
                    r"Tool Name:.*?(?=(\nTool Name:|\Z))",
                    "",
                    text,
                    flags=re.S
                ).strip()
                system_instruction = clean_text
            else:
                mapped_role = "model" if role == "assistant" else "user"

                # Check for Thought → Action → Action Input → Observation format
                action_match = re.search(r"Action:\s*(\w+)", text)
                input_match = re.search(r"Action Input:\s*(\{.*?\})", text, flags=re.S)
                observation_match = re.search(r"Observation:\s*(\{.*\})", text, flags=re.S)

                if action_match and input_match:
                    # Extract thought text
                    user_text = text.split("Action:")[0].strip()
                    thought_part = None
                    if "Thought:" in user_text:
                        thought_text = user_text.replace("Thought:", "").strip()
                        thought_part = types.Part(text=thought_text, thought=True)

                    # Parse function call args
                    try:
                        func_args = json.loads(input_match.group(1))
                    except json.JSONDecodeError:
                        func_args = {}

                    func_name = action_match.group(1)
                    function_part = types.Part(
                        function_call=types.FunctionCall(name=func_name, args=func_args)
                    )

                    # Build model content (thought + function_call)
                    model_parts = []
                    if thought_part:
                        model_parts.append(thought_part)
                    model_parts.append(function_part)

                    contents.append(types.Content(
                        role="model",
                        parts=model_parts
                    ))

                    # If observation exists → separate user content
                    if observation_match:
                        obs_text = observation_match.group(1).strip()
                        try:
                            func_response = json.loads(obs_text)
                        except json.JSONDecodeError:
                            func_response = {"text": obs_text}

                        contents.append(types.Content(
                            role="user",
                            parts=[types.Part(
                                function_response=types.FunctionResponse(
                                    name=func_name,
                                    response=func_response
                                )
                            )]
                        ))

                else:
                    # Default case for normal text
                    contents.append(types.Content(role=mapped_role, parts=[types.Part(text=text)]))

        return contents, system_instruction

    def _to_config(
        self,
        tools: Optional[List[Any]],
        available_functions: Optional[Dict[str, Any]],
        system_instruction: Optional[str]
    ) -> types.GenerateContentConfig:
        genai_tools: List[types.Tool] = []
        seen_func_names = set()
        TYPE_MAP = {"str": "string", "int": "integer", "float": "number", "bool": "boolean"}

        def convert_types(properties: dict) -> dict:
            new_props = {}
            for key, val in properties.items():
                if isinstance(val, dict):
                    t = val.get("type")
                    if t in TYPE_MAP:
                        val["type"] = TYPE_MAP[t]
                    if "properties" in val:
                        val["properties"] = convert_types(val["properties"])
                new_props[key] = val
            return new_props

        func_decls: List[dict] = []

        if tools:
            for t in tools:
                if isinstance(t, dict):
                    if "name" in t and t["name"] not in seen_func_names:
                        if "parameters" in t and "properties" in t["parameters"]:
                            t["parameters"]["properties"] = convert_types(t["parameters"]["properties"])
                        func_decls.append(t)
                        seen_func_names.add(t["name"])
                    elif "function_declarations" in t:
                        for fd in t["function_declarations"]:
                            if fd["name"] not in seen_func_names:
                                if "parameters" in fd and "properties" in fd["parameters"]:
                                    fd["parameters"]["properties"] = convert_types(fd["parameters"]["properties"])
                                func_decls.append(fd)
                                seen_func_names.add(fd["name"])

        if available_functions:
            for func_name, func_obj in available_functions.items():
                if func_name in seen_func_names:
                    continue
                params_schema: Optional[dict] = {"type": "object", "properties": {}}
                args_schema = getattr(func_obj, "args_schema", None)
                try:
                    if args_schema:
                        model_json_schema = getattr(args_schema, "model_json_schema", None)
                        full_schema = model_json_schema() if callable(model_json_schema) else getattr(args_schema, "schema", lambda: {})()
                        params_schema = {
                            "type": "object",
                            "properties": convert_types(full_schema.get("properties", {})),
                            "required": full_schema.get("required", []),
                        }
                except Exception:
                    pass

                func_decl = {
                    "name": func_name,
                    "description": getattr(func_obj, "description", ""),
                    "parameters": params_schema
                }
                func_decls.append(func_decl)
                seen_func_names.add(func_name)

        if func_decls:
            genai_tools.append(types.Tool(function_declarations=func_decls))

        cfg_kwargs: Dict[str, Any] = {}
        if self.temperature is not None:
            cfg_kwargs["temperature"] = self.temperature
        if genai_tools:
            cfg_kwargs["tools"] = genai_tools

        cfg_kwargs["thinking_config"] = types.ThinkingConfig(
            thinking_budget=1000,
            include_thoughts=True
        )

        return types.GenerateContentConfig(
            **cfg_kwargs,
            system_instruction=system_instruction if isinstance(system_instruction, str) else None
        )

    def _parse_response(self, response: Any, messages: List[Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
        thoughts = ""
        text_response = ""
        function_call_result = None

        try:
            parts = response.candidates[0].content.parts
            for part in parts:
                if getattr(part, "thought", None):
                    thoughts += part.text + "\n"
                elif getattr(part, "function_call", None):
                    fc = part.function_call
                    raw_arguments = dict(fc.args) if fc.args else {}

                    # Clean arguments - remove CrewAI metadata
                    clean_arguments = {}
                    for k, v in raw_arguments.items():
                        if k not in ['security_context', 'metadata', 'agent_id']:
                            clean_arguments[k] = v

                    # Check for nested tool parameters
                    if not clean_arguments:
                        for k, v in raw_arguments.items():
                            if isinstance(v, dict) and any(param in v for param in ['url', 'query']):
                                clean_arguments = v
                                break

                    # Fallback: use raw arguments
                    if not clean_arguments:
                        clean_arguments = raw_arguments

                    id_source = f"{fc.name}_{json.dumps(clean_arguments, sort_keys=True)}"
                    call_id = f"call_{hashlib.md5(id_source.encode()).hexdigest()[:8]}"
                    function_call_result = {
                        "tool_calls": [{
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": fc.name,
                                "arguments": json.dumps(clean_arguments)
                            }
                        }]
                    }


                elif getattr(part, "text", None):
                    text_response += part.text

        except (AttributeError, IndexError, KeyError) as e:
            logging.error(f"Error parsing Gemini response: {e}")
            logging.info(f"Raw response: {response}")

        is_react = self._is_react_mode(messages)
        tool_result = self._extract_tool_result_from_messages(messages)

        if is_react:
            if tool_result:
                return f"Observation: {tool_result}"
            if function_call_result:
                thought_prefix = f"Thought: {thoughts.strip()}\n" if thoughts.strip() else "Thought: I need to use a tool.\n"
                if thoughts.strip() and not thoughts.strip().startswith("Thought:"):
                    thought_prefix = f"Thought: {thoughts.strip()}\n"
                tool_call = function_call_result["tool_calls"][0]
                return (
                    f"{thought_prefix}"
                    f"Action: {tool_call['function']['name']}\n"
                    f"Action Input: {tool_call['function']['arguments']}"
                )
            if text_response.strip():
                if thoughts.strip():
                    return f"{thoughts.strip()}\nFinal Answer: {text_response.strip()}"
                else:
                    return f"Thought: I can answer this directly.\nFinal Answer: {text_response.strip()}"

        return function_call_result or text_response or ""

    def _extract_tools_from_system_message(self, messages):
        try:
            tools_list = []
            available_functions = {}
            system_msg = next((m['content'] for m in messages if m.get('role') == 'system'), "")
            if not system_msg:
                return None, None

            tool_pattern = re.compile(
                r"Tool Name:\s*(.+?)\nTool Arguments:\s*(\{.*?\})\nTool Description:\s*(.+?)(?=\nTool Name:|\Z)",
                re.S
            )
            actual_tools = {
                "fast_web_crawler": CrawlWebsiteTool(),
                "FlexibleSerperDevTool": FlexibleSerperDevTool()
            }

            for match in tool_pattern.finditer(system_msg):
                name = match.group(1).strip()
                args_raw = match.group(2).strip()
                desc = match.group(3).strip()
                try:
                    args_schema = json.loads(args_raw.replace("'", '"'))
                except json.JSONDecodeError:
                    args_schema = {}
                func_decl = {
                    "name": name,
                    "description": desc,
                    "parameters": {"type": "object", "properties": args_schema, "required": list(args_schema.keys())}
                }
                tools_list.append(func_decl)
                if name in actual_tools:
                    available_functions[name] = actual_tools[name]

            return tools_list, available_functions
        except Exception as e:
            logging.error(f"Error extracting tools: {e}")
            return None, None

    def _extract_tool_result_from_messages(self, messages):
        if isinstance(messages, list):
            for msg in reversed(messages):
                content = msg.get("content", "")
                if not isinstance(content, str):
                    continue
                lc = content.lower()
                if "tool_result:" in lc:
                    return content.split(":", 1)[1].strip()
                if "function_call_result:" in lc:
                    return content.split(":", 1)[1].strip()
                if content.startswith("{") and content.endswith("}"):
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        continue
        return None

    def supports_function_calling(self) -> bool:
        return True

    def get_context_window_size(self) -> int:
        return 1_000_000
