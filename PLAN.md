# Click MCP Context Passing Fix - Implementation Plan

## Problem Statement

The click-mcp library has a critical issue where parent command context is not passed to child commands when executed through the MCP server. This breaks hierarchical Click command structures that rely on `ctx.obj` for sharing state between parent and child commands.

### Specific Issue
- Commands like `parent --env PRODUCTION child-a` fail
- Child commands execute in isolation without access to parent context
- Parent options (like `--env`) are not recognized by child commands
- `ctx.obj` is None in child commands instead of containing parent state

### Example Failing Case
```python
@click.group()
@click.option('--env', default='DEFAULT')
@click.pass_context
def parent(ctx, env):
    ctx.obj = {'env': env}

@parent.command()
@click.pass_context  
def child_a(ctx):
    # ctx.obj should be {'env': 'PRODUCTION'} but is None
    print(f"Using env: {ctx.obj['env']}")
```

## Root Cause Analysis

The MCP server discovers child commands as individual tools (e.g., `child_a`) rather than as part of their parent command hierarchy. When executing these tools, it calls the child command directly without going through the parent command chain, so parent context is never established.

## Proposed Solution: Click-Native Execution

**Key Insight**: Click's `main()` method naturally handles parent-child command execution and context passing. Instead of building complex hierarchical execution logic, leverage Click's built-in capabilities.

### High-Level Approach

1. **Tool Discovery**: Use hierarchical naming (`parent_child_a`) and include parent parameters in tool schemas
2. **Execution**: Convert MCP tool calls to Click command line format and use Click's `main()` method
3. **Let Click Handle Everything**: Click automatically parses parent options, routes to child commands, and passes context

### Implementation Strategy

#### Phase 1: Update Scanner (click_mcp/scanner.py)
- Modify tool discovery to create hierarchical tool names
- Include parent command parameters in child tool schemas
- Ensure parameter types and descriptions are properly merged

#### Phase 2: Update Server Execution (click_mcp/server.py)
- Replace complex execution logic with simple Click `main()` call
- Build command line arguments from MCP parameters
- Handle different parameter types (flags, options, positional args)

#### Phase 3: Testing
- Update existing tests to use new hierarchical tool names
- Verify all context passing scenarios work correctly
- Ensure backward compatibility for simple commands

## Technical Implementation Details

### Scanner Changes
```python
# Current: discovers "child_a" 
# New: discovers "parent_child_a" with parent parameters included

def _create_hierarchical_tool(parent_cmd, child_cmd, parent_path):
    tool_name = f"{parent_path}_{child_cmd.name}"
    
    # Merge parent and child parameters
    parameters = {}
    
    # Add parent parameters first
    for param in parent_cmd.params:
        parameters[param.name] = create_parameter_schema(param)
    
    # Add child parameters  
    for param in child_cmd.params:
        parameters[param.name] = create_parameter_schema(param)
    
    return Tool(name=tool_name, description=..., inputSchema=...)
```

### Server Execution Changes
```python
def _execute_command(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    # Build Click command line arguments
    args = self._build_click_args(tool_name, parameters)
    
    # Use Click's native execution - this handles everything!
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        self.cli_group.main(args=args, standalone_mode=False)
    
    return {"output": output.getvalue().rstrip()}

def _build_click_args(self, tool_name: str, parameters: Dict[str, Any]) -> List[str]:
    # Convert: "parent_child_a" + {"env": "PROD"} 
    # To: ["--env", "PROD", "child-a"]
    
    if "_" in tool_name:
        parts = tool_name.split("_", 1)
        parent_name = parts[0]
        child_name = parts[1].replace("_", "-")
        
        args = []
        
        # Add parent parameters
        for param_name in self._get_parent_parameters():
            if param_name in parameters:
                args.extend([f"--{param_name}", str(parameters[param_name])])
        
        # Add child command name
        args.append(child_name)
        
        # Add child parameters
        for param_name in self._get_child_parameters(child_name):
            if param_name in parameters:
                if self._is_flag_parameter(child_name, param_name):
                    if parameters[param_name]:
                        args.append(f"--{param_name.replace('_', '-')}")
                elif self._is_positional_parameter(child_name, param_name):
                    args.append(str(parameters[param_name]))
                else:
                    args.extend([f"--{param_name.replace('_', '-')}", str(parameters[param_name])])
        
        return args
```

## Test Cases to Verify

### Core Functionality Tests
1. **Parent with child command**: `parent --env PRODUCTION child-a`
2. **Child with own parameters**: `parent --env STAGING child-b --child-flag test`  
3. **Positional arguments**: `parent --env DEV child-c "hello world"`
4. **Default parent values**: `parent child-a` (should use env=DEFAULT)

### Edge Cases
1. **Multiple parent parameters**: `parent --env PROD --debug child-a`
2. **Boolean flags**: `parent child-b --child-flag` (no value)
3. **Mixed parameter types**: Options, flags, and positional args together

## Files to Modify

### Core Implementation
- `click_mcp/scanner.py` - Update tool discovery for hierarchical commands
- `click_mcp/server.py` - Simplify execution using Click's main() method

### Testing
- `tests/test_hierarchical_commands.py` - Tests for hierarchical command execution with context passing
- `tests/context_cli.py` - Test CLI for hierarchical commands with Click context

## Success Criteria

✅ **All existing tests pass** with updated tool names  
✅ **Parent context properly passed** to child commands  
✅ **All parameter types work** (options, flags, positional)  
✅ **Default values handled** correctly  
✅ **Backward compatibility** maintained for simple commands  
✅ **Code is simpler** than previous complex hierarchical approach  

## Key Implementation Notes

### Critical Insights
1. **Click's main() is the key** - It handles all parsing and context passing automatically
2. **Hierarchical naming works** - Tools like `parent_child_a` are intuitive
3. **Parameter merging is essential** - Child tools must include parent parameters
4. **Argument order matters** - Parent options first, then child command, then child options

### Potential Gotchas
1. **Parameter name conversion** - Handle underscore to dash conversion (`child_flag` → `--child-flag`)
2. **Boolean flag handling** - Flags with no values need special treatment
3. **Positional argument placement** - Must come after command name
4. **Default value handling** - Ensure parent defaults are applied when parameters not provided

### Testing Strategy
- Start with simple parent-child case
- Add complexity incrementally (flags, positional args, defaults)
- Verify output contains both parent and child execution traces
- Ensure error handling works for invalid parameters

## Expected Outcome

A clean, simple solution that leverages Click's native design to properly handle parent-child command execution with full context passing. The implementation should be significantly simpler than complex hierarchical approaches while providing complete functionality.
