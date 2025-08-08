# Click Context Passing Research - Technical Documentation

## Executive Summary

This document contains comprehensive research findings about Click's context passing mechanisms and provides the technical foundation for implementing proper context inheritance in click-mcp to resolve GitHub issue #8.

## Problem Statement

**GitHub Issue #8**: `@click.pass_context` does not work correctly with click-mcp for parent-child command relationships. Parent commands set `ctx.obj` but child commands receive `ctx.obj = None` when executed via MCP.

**Expected Behavior**: 
```bash
parent --env DEFAULT child  # Should pass ctx.obj from parent to child
```

**Current Failure**: click-mcp creates isolated contexts that break Click's context inheritance chain.

## Root Cause Analysis

### Current click-mcp Implementation Problem

**File**: `click_mcp/server.py` lines 83-84
```python
ctx = command.make_context(command.name, args)  # ❌ Creates isolated context
command.invoke(ctx)  # ❌ Executes without parent context
```

**Issues**:
1. **Isolated Context Creation**: No parent-child relationship established
2. **Missing Parent Execution**: Parent command never runs to set `ctx.obj`
3. **Broken Context Chain**: Child commands can't access parent context data

## Click's Context Passing Mechanism

### 1. Context Inheritance Architecture

**File**: `/tmp/click/src/click/core.py` lines 310-314
```python
if obj is None and parent is not None:
    obj = parent.obj
#: the user object stored.
self.obj: t.Any = obj
```

**Key Insight**: Click automatically inherits parent context objects when creating child contexts with `parent=parent_ctx`.

### 2. Context Chain Creation

**File**: `/tmp/click/src/click/core.py` lines 732-738
```python
def _make_sub_context(self, command: Command) -> Context:
    return type(self)(command, info_name=command.name, parent=self)
```

**Key Insight**: Proper child contexts must be created with parent reference for inheritance.

### 3. Context.invoke() Method

**File**: `/tmp/click/src/click/core.py` lines 748-794
- Creates sub-contexts using `self._make_sub_context(other_cmd)` (line 778)
- Automatically fills in default parameters and tracks them in `ctx.params`
- Uses proper context management with `with ctx:` blocks

## Click's Proper Command Execution Pattern

### Group.invoke() - The Gold Standard

**File**: `/tmp/click/src/click/core.py` lines 1820-1830 (non-chain mode)
```python
if not self.chain:
    with ctx:
        cmd_name, cmd, args = self.resolve_command(ctx, args)
        assert cmd is not None
        ctx.invoked_subcommand = cmd_name
        super().invoke(ctx)  # ✅ Execute parent command first
        sub_ctx = cmd.make_context(cmd_name, args, parent=ctx)  # ✅ Create child with parent
        with sub_ctx:
            return _process_result(sub_ctx.command.invoke(sub_ctx))  # ✅ Execute child
```

**Critical Success Factors**:
1. **Parent Execution First**: `super().invoke(ctx)` runs parent to set up `ctx.obj`
2. **Proper Context Chain**: `parent=ctx` parameter creates inheritance relationship
3. **Context Management**: `with ctx:` blocks ensure proper resource management
4. **Command Resolution**: `resolve_command()` properly identifies command hierarchy

## Click Test Patterns Validation

### Test Case Pattern from `/tmp/click/tests/test_context.py` lines 37-57

```python
@click.group()
@click.pass_context
def cli(ctx):
    ctx.obj = Foo()
    ctx.obj.title = "test"

@cli.command()
@pass_foo
def test(foo):
    click.echo(foo.title)

result = runner.invoke(cli, ["test"])  # ✅ Single entry point executes full chain
assert result.output == "test\n"
```

**Key Insights**:
1. **Single Entry Point**: `runner.invoke(cli, ["test"])` executes parent → child chain
2. **No Isolated Execution**: Never call child commands directly
3. **Automatic Context Management**: Click handles context creation and inheritance
4. **Command Resolution**: Click resolves "test" as child of "cli" group

## Implementation Strategy for click-mcp

### 1. Command Hierarchy Detection

**Challenge**: Parse MCP tool calls to identify parent-child command relationships.

**Example**: 
- MCP Tool Call: `parent_child` with args `["--env", "DEFAULT"]`
- Should execute: `parent --env DEFAULT child`

**Solution**: 
```python
def parse_command_hierarchy(tool_name, args):
    """
    Parse tool name like 'parent_child' and args to identify:
    - parent_command: 'parent'
    - parent_args: ['--env', 'DEFAULT'] 
    - child_command: 'child'
    - child_args: []
    """
```

### 2. Context Chain Execution Algorithm

**Replace isolated execution with proper context chain**:

```python
def execute_command_chain(cli_group, command_chain):
    """
    Execute command chain with proper context inheritance.
    
    Args:
        cli_group: Root Click group
        command_chain: List of (command, args) tuples in execution order
    """
    parent_ctx = None
    result = None
    
    for cmd_name, cmd_args in command_chain:
        if parent_ctx is None:
            # Root command - create initial context
            cmd = cli_group.get_command(None, cmd_name)
            ctx = cmd.make_context(cmd_name, cmd_args)
        else:
            # Child command - create with parent context
            cmd = parent_ctx.command.get_command(parent_ctx, cmd_name)
            ctx = cmd.make_context(cmd_name, cmd_args, parent=parent_ctx)
        
        with ctx:
            result = cmd.invoke(ctx)
            parent_ctx = ctx  # Pass context to next level
    
    return result
```

### 3. Integration with click-mcp Scanner

**Current Scanner Issue**: `click_mcp/scanner.py` treats each command as independent MCP tool.

**Solution**: Detect context dependencies and create compound tools:
```python
def detect_context_dependencies(cli_group):
    """
    Scan CLI for @click.pass_context usage and create compound tools
    that preserve parent-child relationships.
    """
    # Identify commands that use @click.pass_context
    # Create MCP tools that execute full command chains
    # Example: 'parent_child' tool instead of separate 'parent' and 'child' tools
```

## Alternative Approaches Considered

### 1. Click Testing Runner Pattern
```python
from click.testing import CliRunner
runner = CliRunner()
result = runner.invoke(cli, ["parent", "--env", "DEFAULT", "child"])
```
**Pros**: Uses Click's proven execution pattern
**Cons**: Requires test runner environment, may have overhead

### 2. Context.invoke() Method
```python
@click.command()
@click.pass_context
def parent_cmd(ctx):
    ctx.obj = {"env": "DEFAULT"}
    return ctx.invoke(child_cmd)
```
**Pros**: Clean programmatic invocation
**Cons**: Requires restructuring command definitions

### 3. Manual Context Chain Building
```python
def build_context_chain(commands):
    contexts = []
    parent = None
    for cmd, args in commands:
        ctx = cmd.make_context(cmd.name, args, parent=parent)
        contexts.append(ctx)
        parent = ctx
    return contexts
```
**Pros**: Full control over context creation
**Cons**: More complex, potential for errors

## Recommended Implementation Plan

### Phase 1: Core Context Chain Execution
1. Implement `execute_command_chain()` function in `server.py`
2. Replace isolated `command.make_context()` calls
3. Add command hierarchy parsing logic

### Phase 2: Scanner Enhancement
1. Detect `@click.pass_context` usage in commands
2. Create compound MCP tools for parent-child relationships
3. Update tool naming and argument handling

### Phase 3: Testing and Validation
1. Create test case reproducing GitHub issue #8
2. Validate context inheritance works correctly
3. Test edge cases and error handling

## Success Criteria

1. **Context Inheritance**: Child commands receive parent `ctx.obj` correctly
2. **Command Execution**: Parent commands execute before children to set up context
3. **Error Handling**: Proper error propagation through context chain
4. **Resource Management**: Proper context cleanup with `with ctx:` blocks
5. **Backward Compatibility**: Existing single commands continue to work

## Risk Mitigation

1. **Breaking Changes**: Implement feature flag for new context execution
2. **Performance**: Monitor execution overhead of context chain building
3. **Complexity**: Start with simple parent-child cases, expand gradually
4. **Testing**: Comprehensive test coverage for context passing scenarios

## References

- Click Source Code: `/tmp/click/src/click/core.py`
- Click Test Cases: `/tmp/click/tests/test_context.py`
- GitHub Issue #8: https://github.com/crowecawcaw/click-mcp/issues/8
- Click Issue #942: https://github.com/pallets/click/issues/942 (similar problem, resolved)
