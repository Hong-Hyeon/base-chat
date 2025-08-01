from typing import Dict, Any, List, Union
from langgraph.graph import StateGraph, END
from app.models.chat import Message, ConversationState, ChatRequest, MCPToolCall, MessageRole
from app.utils.logger import get_logger
from datetime import datetime
import asyncio


logger = get_logger("conversation_graph")


def serialize_message(message: Message) -> Dict[str, Any]:
    """Serialize a Message object to ensure JSON compatibility."""
    return {
        "role": message.role.value,
        "content": message.content,
        "timestamp": message.timestamp.isoformat() if message.timestamp else None
    }


def serialize_messages(messages: List[Message]) -> List[Dict[str, Any]]:
    """Serialize a list of Message objects."""
    return [serialize_message(msg) for msg in messages]


def serialize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize metadata to ensure JSON compatibility."""
    serialized = {}
    for key, value in metadata.items():
        if isinstance(value, datetime):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized


def serialize_mcp_tool_calls(tool_calls: List[MCPToolCall]) -> List[Dict[str, Any]]:
    """Serialize MCP tool calls to ensure JSON compatibility."""
    return [tool_call.model_dump() for tool_call in tool_calls]


def ensure_conversation_state(state: Union[Dict[str, Any], ConversationState]) -> ConversationState:
    """Ensure state is a ConversationState object, converting from dict if needed."""
    if isinstance(state, ConversationState):
        return state
    
    # Convert dict to ConversationState
    messages = []
    for msg_dict in state.get("messages", []):
        if isinstance(msg_dict, dict):
            messages.append(Message(
                role=MessageRole(msg_dict["role"]),  # Use MessageRole enum directly
                content=msg_dict["content"],
                timestamp=msg_dict.get("timestamp")
            ))
        else:
            messages.append(msg_dict)
    
    return ConversationState(
        messages=messages,
        metadata=state.get("metadata", {}),
        session_id=state.get("session_id"),
        mcp_tools_needed=state.get("mcp_tools_needed", []),
        mcp_tool_calls=state.get("mcp_tool_calls", []),
        mcp_tools_available=state.get("mcp_tools_available", [])
    )


def create_conversation_graph():
    """Create a LangGraph workflow for conversation management with MCP tool support."""
    
    # Define the state schema
    workflow = StateGraph(ConversationState)
    
    # Add nodes
    workflow.add_node("validate_input", validate_user_input)
    workflow.add_node("load_mcp_tools", load_mcp_tools)
    workflow.add_node("analyze_user_intent", analyze_user_intent)
    workflow.add_node("call_mcp_tools", call_mcp_tools)
    workflow.add_node("prepare_llm_request", prepare_llm_request)
    workflow.add_node("call_llm_agent", call_llm_agent)
    workflow.add_node("generate_direct_response", generate_direct_response)
    workflow.add_node("process_llm_response", process_llm_response)
    workflow.add_node("format_output", format_conversation_output)
    
    # Define the workflow with conditional routing
    workflow.set_entry_point("validate_input")
    workflow.add_edge("validate_input", "load_mcp_tools")
    workflow.add_edge("load_mcp_tools", "analyze_user_intent")
    
    # Conditional routing based on whether tools are needed
    workflow.add_conditional_edges(
        "analyze_user_intent",
        route_based_on_tools_needed,
        {
            "tools_needed": "call_mcp_tools",
            "no_tools": "generate_direct_response"
        }
    )
    
    workflow.add_edge("call_mcp_tools", "prepare_llm_request")
    workflow.add_edge("prepare_llm_request", "call_llm_agent")
    workflow.add_edge("call_llm_agent", "process_llm_response")
    workflow.add_edge("generate_direct_response", "process_llm_response")
    workflow.add_edge("process_llm_response", "format_output")
    workflow.add_edge("format_output", END)
    
    return workflow.compile()


def route_based_on_tools_needed(state: Union[Dict[str, Any], ConversationState]) -> str:
    """Route to next node based on whether MCP tools are needed."""
    conv_state = ensure_conversation_state(state)
    
    if conv_state.mcp_tools_needed:
        logger.info(f"Routing to tools_needed: {conv_state.mcp_tools_needed}")
        return "tools_needed"
    else:
        logger.info("Routing to no_tools - proceeding directly to LLM")
        return "no_tools"


async def validate_user_input(state: Union[Dict[str, Any], ConversationState]) -> Dict[str, Any]:
    """Validate user input and ensure proper message format."""
    logger.info("Validating user input")
    
    conv_state = ensure_conversation_state(state)
    
    # Ensure we have messages
    if not conv_state.messages:
        raise ValueError("No messages provided in conversation state")
    
    # Validate the last message is from user
    last_message = conv_state.messages[-1]
    if last_message.role.value != "user":
        raise ValueError("Last message must be from user")
    
    # Add validation metadata
    conv_state.metadata["input_validated"] = True
    conv_state.metadata["user_message_count"] = len([m for m in conv_state.messages if m.role.value == "user"])
    conv_state.metadata["assistant_message_count"] = len([m for m in conv_state.messages if m.role.value == "assistant"])
    
    logger.info(f"Input validated. User messages: {conv_state.metadata['user_message_count']}, Assistant messages: {conv_state.metadata['assistant_message_count']}")
    
    return {
        "messages": serialize_messages(conv_state.messages),
        "metadata": serialize_metadata(conv_state.metadata),
        "session_id": conv_state.session_id,
        "mcp_tools_needed": conv_state.mcp_tools_needed,
        "mcp_tool_calls": serialize_mcp_tool_calls(conv_state.mcp_tool_calls),
        "mcp_tools_available": conv_state.mcp_tools_available
    }


async def load_mcp_tools(state: Union[Dict[str, Any], ConversationState]) -> Dict[str, Any]:
    """Load available MCP tools from the MCP server."""
    logger.info("Loading available MCP tools")
    
    conv_state = ensure_conversation_state(state)
    
    try:
        from app.services.mcp_client import MCPClient
        mcp_client = MCPClient()
        
        # Get available tools
        tools_data = await mcp_client.list_tools()
        conv_state.mcp_tools_available = tools_data.get("tools", [])
        
        logger.info(f"Loaded {len(conv_state.mcp_tools_available)} MCP tools")
        
        # Log each tool
        for tool in conv_state.mcp_tools_available:
            logger.info(f"Tool: {tool.get('name', 'unknown')} - {tool.get('description', 'no description')}")
        
    except Exception as e:
        logger.error(f"Failed to load MCP tools: {str(e)}")
        conv_state.mcp_tools_available = []
    
    return {
        "messages": serialize_messages(conv_state.messages),
        "metadata": serialize_metadata(conv_state.metadata),
        "session_id": conv_state.session_id,
        "mcp_tools_needed": conv_state.mcp_tools_needed,
        "mcp_tool_calls": serialize_mcp_tool_calls(conv_state.mcp_tool_calls),
        "mcp_tools_available": conv_state.mcp_tools_available
    }


async def analyze_user_intent(state: Union[Dict[str, Any], ConversationState]) -> Dict[str, Any]:
    """Analyze user intent using LLM to determine if MCP tools are needed with caching."""
    logger.info("Analyzing user intent using LLM for MCP tool requirements")
    
    conv_state = ensure_conversation_state(state)
    
    try:
        # Get the last user message
        last_message = conv_state.messages[-1]
        user_content = last_message.content
        logger.info(f"User content: '{user_content}'")
        
        # Check cache first for intent analysis
        from app.services.cache_manager import get_cache_manager
        cache_manager = await get_cache_manager()
        
        cached_intent = await cache_manager.get_intent_cache(user_content)
        if cached_intent:
            logger.info("Intent analysis result retrieved from cache")
            conv_state.mcp_tools_needed = cached_intent.get("tools_needed", [])
            conv_state.metadata["llm_tool_decision"] = cached_intent.get("llm_decision", "")
            conv_state.metadata["llm_tool_analysis"] = True
            conv_state.metadata["cached_intent"] = True
            
            if conv_state.mcp_tools_needed:
                logger.info(f"Cached intent decided tools needed: {conv_state.mcp_tools_needed}")
            else:
                logger.info("Cached intent decided no tools needed")
            
            return {
                "messages": serialize_messages(conv_state.messages),
                "metadata": serialize_metadata(conv_state.metadata),
                "session_id": conv_state.session_id,
                "mcp_tools_needed": conv_state.mcp_tools_needed,
                "mcp_tool_calls": serialize_mcp_tool_calls(conv_state.mcp_tool_calls),
                "mcp_tools_available": conv_state.mcp_tools_available
            }
        
        # Cache miss - perform intent analysis
        logger.info("Intent cache miss - performing LLM analysis")
        
        # Get available tool names and descriptions
        available_tools = []
        for tool in conv_state.mcp_tools_available:
            available_tools.append({
                "name": tool.get("name", ""),
                "description": tool.get("description", "")
            })
        
        logger.info(f"Available tools: {[tool['name'] for tool in available_tools]}")
        
        # Create LLM prompt for tool decision
        tool_decision_prompt = create_tool_decision_prompt(user_content, available_tools)
        
        # Call LLM to make tool decision
        from app.services.llm_client import LLMClient
        llm_client = LLMClient()
        
        # Create temporary message for tool decision
        decision_message = Message(
            role=MessageRole.USER,
            content=tool_decision_prompt,
            timestamp=datetime.utcnow()
        )
        
        # Create request for tool decision
        decision_request = ChatRequest(
            messages=[decision_message],
            stream=False,
            temperature=0.1,  # Low temperature for consistent decisions
            max_tokens=500,
            model=conv_state.metadata.get("model", "gpt-3.5-turbo")
        )
        
        # Get LLM decision
        decision_response = await llm_client.generate_text(decision_request)
        llm_decision = decision_response.get("response", "")
        
        logger.info(f"LLM tool decision: {llm_decision}")
        
        # Parse LLM decision
        tools_needed = parse_llm_tool_decision(llm_decision, available_tools)
        conv_state.mcp_tools_needed = tools_needed
        
        # Store decision metadata
        conv_state.metadata["llm_tool_decision"] = llm_decision
        conv_state.metadata["llm_tool_analysis"] = True
        
        # Cache the intent analysis result
        intent_result = {
            "tools_needed": tools_needed,
            "llm_decision": llm_decision,
            "user_content": user_content
        }
        await cache_manager.set_intent_cache(user_content, intent_result)
        
        if tools_needed:
            logger.info(f"LLM decided tools needed: {tools_needed}")
        else:
            logger.info("LLM decided no tools needed - proceeding directly to response generation")
        
    except Exception as e:
        logger.error(f"Failed to analyze user intent with LLM: {str(e)}")
        conv_state.mcp_tools_needed = []
        conv_state.metadata["llm_tool_analysis_failed"] = True
    
    return {
        "messages": serialize_messages(conv_state.messages),
        "metadata": serialize_metadata(conv_state.metadata),
        "session_id": conv_state.session_id,
        "mcp_tools_needed": conv_state.mcp_tools_needed,
        "mcp_tool_calls": serialize_mcp_tool_calls(conv_state.mcp_tool_calls),
        "mcp_tools_available": conv_state.mcp_tools_available
    }


def create_tool_decision_prompt(user_content: str, available_tools: List[Dict[str, str]]) -> str:
    """Create a prompt for the LLM to decide which tools to use."""
    
    tools_description = "\n".join([
        f"- {tool['name']}: {tool['description']}"
        for tool in available_tools
    ])
    
    prompt = f"""You are a tool selection assistant. Your job is to analyze the user's request and decide whether any MCP tools should be used.

Available MCP tools:
{tools_description}

User request: "{user_content}"

Please analyze the user's request and respond with ONLY a JSON object in this exact format:

{{
  "use_tools": true/false,
  "tools": ["tool_name1", "tool_name2"] or [],
  "reasoning": "brief explanation of your decision"
}}

Rules:
1. Only use tools if they are clearly needed for the user's request
2. For echo tool: use when user wants something repeated or echoed back
3. For web_search tool: use when user asks for current information, news, facts, or anything that requires up-to-date data
4. If no tools are needed, respond with "use_tools": false and "tools": []
5. Be conservative - only use tools when they add clear value

Respond with ONLY the JSON object, no other text:"""

    return prompt


def parse_llm_tool_decision(llm_response: str, available_tools: List[Dict[str, str]]) -> List[str]:
    """Parse the LLM's tool decision response."""
    import json
    import re
    
    try:
        # Try to extract JSON from the response
        # Look for JSON pattern in the response
        json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            decision = json.loads(json_str)
            
            # Validate the decision
            if isinstance(decision, dict) and "use_tools" in decision and "tools" in decision:
                if decision["use_tools"] and isinstance(decision["tools"], list):
                    # Filter to only include available tools
                    available_tool_names = [tool["name"] for tool in available_tools]
                    valid_tools = [tool for tool in decision["tools"] if tool in available_tool_names]
                    
                    logger.info(f"Parsed tool decision: {decision}")
                    logger.info(f"Valid tools selected: {valid_tools}")
                    
                    return valid_tools
                else:
                    logger.info("LLM decided no tools needed")
                    return []
        
        # Fallback: if JSON parsing fails, try keyword-based fallback
        logger.warning("Failed to parse LLM JSON response, using fallback logic")
        return fallback_tool_selection(llm_response, available_tools)
        
    except Exception as e:
        logger.error(f"Error parsing LLM tool decision: {str(e)}")
        logger.error(f"LLM response was: {llm_response}")
        return fallback_tool_selection(llm_response, available_tools)


def fallback_tool_selection(llm_response: str, available_tools: List[Dict[str, str]]) -> List[str]:
    """Fallback tool selection logic if LLM parsing fails."""
    available_tool_names = [tool["name"] for tool in available_tools]
    selected_tools = []
    
    # Simple keyword matching as fallback
    response_lower = llm_response.lower()
    
    if "echo" in available_tool_names and any(word in response_lower for word in ["echo", "repeat"]):
        selected_tools.append("echo")
    
    if "web_search" in available_tool_names and any(word in response_lower for word in ["web_search", "search", "web search"]):
        selected_tools.append("web_search")
    
    logger.info(f"Fallback tool selection: {selected_tools}")
    return selected_tools


async def call_mcp_tools(state: Union[Dict[str, Any], ConversationState]) -> Dict[str, Any]:
    """Call MCP tools in parallel and collect results."""
    conv_state = ensure_conversation_state(state)
    
    logger.info(f"Calling MCP tools: {conv_state.mcp_tools_needed}")
    
    try:
        from app.services.mcp_client import MCPClient
        mcp_client = MCPClient()
        
        # Prepare tool calls
        tool_calls = []
        for tool_name in conv_state.mcp_tools_needed:
            # Find tool info
            tool_info = next((tool for tool in conv_state.mcp_tools_available if tool.get("name") == tool_name), None)
            
            if tool_info:
                # Prepare input data based on tool type
                input_data = prepare_tool_input(tool_name, conv_state.messages[-1].content)
                
                tool_call = MCPToolCall(
                    tool_name=tool_name,
                    input_data=input_data
                )
                tool_calls.append(tool_call)
        
        # Call tools in parallel
        async def call_single_tool(tool_call: MCPToolCall) -> MCPToolCall:
            try:
                result = await mcp_client.call_tool(tool_call.tool_name, tool_call.input_data)
                tool_call.result = result
                tool_call.success = True
                logger.info(f"Tool {tool_call.tool_name} called successfully")
            except Exception as e:
                tool_call.error = str(e)
                tool_call.success = False
                logger.error(f"Tool {tool_call.tool_name} failed: {str(e)}")
            return tool_call
        
        # Execute all tool calls in parallel
        if tool_calls:
            results = await asyncio.gather(*[call_single_tool(tool_call) for tool_call in tool_calls])
            conv_state.mcp_tool_calls = results
            logger.info(f"Completed {len(results)} tool calls")
        
    except Exception as e:
        logger.error(f"Failed to call MCP tools: {str(e)}")
        conv_state.mcp_tool_calls = []
    
    return {
        "messages": serialize_messages(conv_state.messages),
        "metadata": serialize_metadata(conv_state.metadata),
        "session_id": conv_state.session_id,
        "mcp_tools_needed": conv_state.mcp_tools_needed,
        "mcp_tool_calls": serialize_mcp_tool_calls(conv_state.mcp_tool_calls),
        "mcp_tools_available": conv_state.mcp_tools_available
    }


def prepare_tool_input(tool_name: str, user_content: str) -> Dict[str, Any]:
    """Prepare input data for MCP tools based on LLM decision and user content."""
    if tool_name == "echo":
        # For echo tool, use the original user content
        return {"message": user_content, "prefix": "Echo: "}
    
    elif tool_name == "web_search":
        # For web search tool, use the original user content as query
        return {
            "query": user_content,
            "max_results": 5,
            "search_engine": "duckduckgo"
        }
    
    # Default case - pass the full user content
    return {"input": user_content}


async def prepare_llm_request(state: Union[Dict[str, Any], ConversationState]) -> Dict[str, Any]:
    """Prepare the request for the LLM agent, including MCP tool results if available."""
    logger.info("Preparing LLM request")
    
    conv_state = ensure_conversation_state(state)
    
    try:
        # Get the last user message
        last_user_message = conv_state.messages[-1]
        
        # Prepare context for LLM
        context_parts = []
        
        # Add user's original message
        context_parts.append(f"User: {last_user_message.content}")
        
        # Add MCP tool results if available
        if conv_state.mcp_tool_calls:
            context_parts.append("\nMCP Tool Results:")
            for tool_call in conv_state.mcp_tool_calls:
                if tool_call.success and tool_call.result:
                    context_parts.append(f"- {tool_call.tool_name}: {tool_call.result}")
                else:
                    context_parts.append(f"- {tool_call.tool_name}: Failed - {tool_call.error}")
        
        # Combine context
        enhanced_content = "\n".join(context_parts)
        
        # Create enhanced message for LLM
        enhanced_message = Message(
            role=conv_state.messages[-1].role,
            content=enhanced_content,
            timestamp=datetime.utcnow()
        )
        
        # Update messages with enhanced content
        enhanced_messages = conv_state.messages[:-1] + [enhanced_message]
        conv_state.messages = enhanced_messages
        
        # Add metadata about MCP tool usage
        if conv_state.mcp_tool_calls:
            successful_tools = [tc.tool_name for tc in conv_state.mcp_tool_calls if tc.success]
            failed_tools = [tc.tool_name for tc in conv_state.mcp_tool_calls if not tc.success]
            
            conv_state.metadata["mcp_tools_used"] = successful_tools
            conv_state.metadata["mcp_tools_failed"] = failed_tools
            conv_state.metadata["mcp_tools_called"] = True
        
        logger.info("LLM request prepared successfully")
        
    except Exception as e:
        logger.error(f"Failed to prepare LLM request: {str(e)}")
    
    return {
        "messages": serialize_messages(conv_state.messages),
        "metadata": serialize_metadata(conv_state.metadata),
        "session_id": conv_state.session_id,
        "mcp_tools_needed": conv_state.mcp_tools_needed,
        "mcp_tool_calls": serialize_mcp_tool_calls(conv_state.mcp_tool_calls),
        "mcp_tools_available": conv_state.mcp_tools_available
    }


async def call_llm_agent(state: Union[Dict[str, Any], ConversationState]) -> Dict[str, Any]:
    """Call the LLM agent service to generate a response."""
    logger.info("Calling LLM agent")
    
    conv_state = ensure_conversation_state(state)
    
    try:
        from app.services.llm_client import LLMClient
        llm_client = LLMClient()
        
        # Create request for LLM agent
        llm_request = ChatRequest(
            messages=conv_state.messages,
            stream=False,  # We'll handle streaming separately
            temperature=conv_state.metadata.get("temperature", 0.7),
            max_tokens=conv_state.metadata.get("max_tokens"),
            model=conv_state.metadata.get("model", "gpt-4")
        )
        
        # Call LLM agent
        llm_response = await llm_client.generate_text(llm_request)
        
        # Create assistant message from response
        assistant_message = Message(
            role="assistant",
            content=llm_response["response"],  # Access as dictionary
            timestamp=datetime.utcnow()
        )
        
        # Add assistant message to conversation
        conv_state.messages.append(assistant_message)
        
        # Add LLM response metadata
        conv_state.metadata["llm_response_received"] = True
        conv_state.metadata["llm_model"] = llm_response.get("model")
        conv_state.metadata["llm_usage"] = llm_response.get("usage")
        conv_state.metadata["llm_finish_reason"] = llm_response.get("finish_reason")
        
        logger.info("LLM agent called successfully")
        
    except Exception as e:
        logger.error(f"Failed to call LLM agent: {str(e)}")
        # Create error message
        error_message = Message(
            role="assistant",
            content=f"I apologize, but I encountered an error while processing your request: {str(e)}",
            timestamp=datetime.utcnow()
        )
        conv_state.messages.append(error_message)
    
    return {
        "messages": serialize_messages(conv_state.messages),
        "metadata": serialize_metadata(conv_state.metadata),
        "session_id": conv_state.session_id,
        "mcp_tools_needed": conv_state.mcp_tools_needed,
        "mcp_tool_calls": serialize_mcp_tool_calls(conv_state.mcp_tool_calls),
        "mcp_tools_available": conv_state.mcp_tools_available
    }


async def generate_direct_response(state: Union[Dict[str, Any], ConversationState]) -> Dict[str, Any]:
    """Generate a direct response from the LLM when no tools are needed."""
    logger.info("Generating direct response from LLM")
    
    conv_state = ensure_conversation_state(state)
    
    try:
        from app.services.llm_client import LLMClient
        llm_client = LLMClient()
        
        # Create a simple prompt for the LLM to generate a response
        prompt = f"""You are an AI assistant. You are currently in a conversation with a user.

The user's last message was: "{conv_state.messages[-1].content}"

Please generate a response to the user's message.

Your response:"""
        
        # Create request for LLM agent
        llm_request = ChatRequest(
            messages=[Message(role=MessageRole.USER, content=prompt, timestamp=datetime.utcnow())],
            stream=False,
            temperature=0.7,  # Default temperature for direct response
            max_tokens=500,
            model=conv_state.metadata.get("model", "gpt-3.5-turbo")
        )
        
        # Call LLM agent
        llm_response = await llm_client.generate_text(llm_request)
        
        # Create assistant message from response
        assistant_message = Message(
            role="assistant",
            content=llm_response["response"],  # Access as dictionary
            timestamp=datetime.utcnow()
        )
        
        # Add assistant message to conversation
        conv_state.messages.append(assistant_message)
        
        # Add LLM response metadata
        conv_state.metadata["llm_response_received"] = True
        conv_state.metadata["llm_model"] = llm_response.get("model")
        conv_state.metadata["llm_usage"] = llm_response.get("usage")
        conv_state.metadata["llm_finish_reason"] = llm_response.get("finish_reason")
        
        logger.info("Direct response generated successfully")
        
    except Exception as e:
        logger.error(f"Failed to generate direct response from LLM: {str(e)}")
        # Create error message
        error_message = Message(
            role="assistant",
            content=f"I apologize, but I encountered an error while generating a response: {str(e)}",
            timestamp=datetime.utcnow()
        )
        conv_state.messages.append(error_message)
    
    return {
        "messages": serialize_messages(conv_state.messages),
        "metadata": serialize_metadata(conv_state.metadata),
        "session_id": conv_state.session_id,
        "mcp_tools_needed": conv_state.mcp_tools_needed,
        "mcp_tool_calls": serialize_mcp_tool_calls(conv_state.mcp_tool_calls),
        "mcp_tools_available": conv_state.mcp_tools_available
    }


async def process_llm_response(state: Union[Dict[str, Any], ConversationState]) -> Dict[str, Any]:
    """Process the LLM response and prepare for output formatting."""
    logger.info("Processing LLM response")
    
    conv_state = ensure_conversation_state(state)
    
    try:
        # Get the last assistant message
        last_assistant_message = conv_state.messages[-1]
        
        # Add processing metadata
        conv_state.metadata["response_processed"] = True
        conv_state.metadata["response_length"] = len(last_assistant_message.content)
        conv_state.metadata["final_response"] = last_assistant_message.content
        
        logger.info("LLM response processed successfully")
        
    except Exception as e:
        logger.error(f"Failed to process LLM response: {str(e)}")
    
    return {
        "messages": serialize_messages(conv_state.messages),
        "metadata": serialize_metadata(conv_state.metadata),
        "session_id": conv_state.session_id,
        "mcp_tools_needed": conv_state.mcp_tools_needed,
        "mcp_tool_calls": serialize_mcp_tool_calls(conv_state.mcp_tool_calls),
        "mcp_tools_available": conv_state.mcp_tools_available
    }


async def format_conversation_output(state: Union[Dict[str, Any], ConversationState]) -> Dict[str, Any]:
    """Format the final conversation output."""
    logger.info("Formatting conversation output")
    
    conv_state = ensure_conversation_state(state)
    
    try:
        # Add final formatting metadata
        conv_state.metadata["output_formatted"] = True
        conv_state.metadata["conversation_complete"] = True
        
        # Ensure MCP tool metadata is included
        if conv_state.mcp_tool_calls:
            successful_tools = [tc.tool_name for tc in conv_state.mcp_tool_calls if tc.success]
            failed_tools = [tc.tool_name for tc in conv_state.mcp_tool_calls if not tc.success]
            
            conv_state.metadata["mcp_tools_used"] = successful_tools
            conv_state.metadata["mcp_tools_failed"] = failed_tools
        
        logger.info("Conversation output formatted successfully")
        
    except Exception as e:
        logger.error(f"Failed to format conversation output: {str(e)}")
    
    return {
        "messages": serialize_messages(conv_state.messages),
        "metadata": serialize_metadata(conv_state.metadata),
        "session_id": conv_state.session_id,
        "mcp_tools_needed": conv_state.mcp_tools_needed,
        "mcp_tool_calls": serialize_mcp_tool_calls(conv_state.mcp_tool_calls),
        "mcp_tools_available": conv_state.mcp_tools_available
    }


# Global graph instance
conversation_graph = create_conversation_graph() 