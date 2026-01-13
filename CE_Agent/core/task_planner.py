from ..models.core_models import ExecutionPlan, SubTask, TaskState
from ..models.base import ToolMetadata, ToolCategory
from typing import List, Dict, Any, Optional
import re


class TaskType:
    """任务分类类型。"""
    DATA_STRUCTURE_ANALYSIS = "DATA_STRUCTURE_ANALYSIS"
    FUNCTION_ANALYSIS = "FUNCTION_ANALYSIS"
    PATTERN_SEARCH = "PATTERN_SEARCH"
    BREAKPOINT_DEBUGGING = "BREAKPOINT_DEBUGGING"
    COMPREHENSIVE_ANALYSIS = "COMPREHENSIVE_ANALYSIS"


class TaskPlanner:
    """AI 代理的任务规划器。"""
    
    def __init__(self, tool_registry):
        """
        初始化任务规划器。
        
        Args:
            tool_registry: 用于工具选择的工具注册表
        """
        self.tool_registry = tool_registry
        self.logger = None  # 将由代理设置
        
    def plan(self, request: str) -> ExecutionPlan:
        """
        根据用户请求规划任务。
        
        Args:
            request: 用户的请求
            
        Returns:
            任务的执行计划
        """
        # 从请求中识别意图
        intent = self.identify_intent(request)
        
        # 分类任务类型
        task_type = self.classify_task(intent)
        
        # 将任务分解为子任务
        subtasks = self.decompose_task(task_type, request)
        
        # 生成执行计划
        plan = ExecutionPlan(
            task_id=self._generate_task_id(),
            task_type=task_type,
            description=request,
            subtasks=subtasks,
            estimated_steps=len(subtasks)
        )
        
        return plan
    
    def identify_intent(self, request: str) -> str:
        """
        Identify the intent from the user request.
        
        Args:
            request: The user's request
            
        Returns:
            The identified intent
        """
        request_lower = request.lower()
        
        # Define common intent patterns
        intent_patterns = [
            (r'(find|locate|search|scan|look for|find pattern)', 'search'),
            (r'(analyze|examine|inspect|study|investigate)', 'analyze'),
            (r'(read|view|get|retrieve|fetch|obtain)', 'read'),
            (r'(modify|change|alter|update|set|write)', 'modify'),
            (r'(debug|breakpoint|monitor|watch)', 'debug'),
            (r'(structure|data structure|struct|object)', 'structure'),
            (r'(function|code|disassemble|assembly)', 'function'),
            (r'(memory|address|pointer)', 'memory')
        ]
        
        for pattern, intent in intent_patterns:
            if re.search(pattern, request_lower):
                return intent
                
        return 'general'
    
    def classify_task(self, intent: str) -> str:
        """
        Classify the task based on the identified intent.
        
        Args:
            intent: The identified intent
            
        Returns:
            The task type
        """
        intent_to_task_map = {
            'structure': TaskType.DATA_STRUCTURE_ANALYSIS,
            'function': TaskType.FUNCTION_ANALYSIS,
            'search': TaskType.PATTERN_SEARCH,
            'debug': TaskType.BREAKPOINT_DEBUGGING,
            'analyze': TaskType.COMPREHENSIVE_ANALYSIS,
            'general': TaskType.COMPREHENSIVE_ANALYSIS
        }
        
        return intent_to_task_map.get(intent, TaskType.COMPREHENSIVE_ANALYSIS)
    
    def decompose_task(self, task_type: str, request: str) -> List[SubTask]:
        """
        Decompose a task into subtasks.
        
        Args:
            task_type: The type of task
            request: The user's request
            
        Returns:
            A list of subtasks
        """
        subtasks = []
        
        if task_type == TaskType.DATA_STRUCTURE_ANALYSIS:
            # Analyze data structures in memory
            subtasks.extend([
                SubTask(
                    id=1,
                    description="Identify the target process for analysis",
                    tools=["get_process_info"],
                    expected_output="Process information including PID and name",
                    dependencies=[]
                ),
                SubTask(
                    id=2,
                    description="Scan memory regions for interesting data",
                    tools=["get_memory_regions"],
                    expected_output="List of accessible memory regions",
                    dependencies=[1]
                ),
                SubTask(
                    id=3,
                    description="Perform pattern scans to identify data structures",
                    tools=["scan_all", "generate_signature"],
                    expected_output="Potential data structure locations and signatures",
                    dependencies=[2]
                ),
                SubTask(
                    id=4,
                    description="Analyze identified data structures",
                    tools=["disassemble", "analyze_function"],
                    expected_output="Detailed analysis of data structures",
                    dependencies=[3]
                )
            ])
            
        elif task_type == TaskType.FUNCTION_ANALYSIS:
            # Analyze functions and code
            subtasks.extend([
                SubTask(
                    id=1,
                    description="Locate the target function or module",
                    tools=["enum_modules", "get_symbol_address"],
                    expected_output="Function addresses and module information",
                    dependencies=[]
                ),
                SubTask(
                    id=2,
                    description="Disassemble the function to understand its structure",
                    tools=["disassemble", "get_instruction_info"],
                    expected_output="Assembly code and instruction details",
                    dependencies=[1]
                ),
                SubTask(
                    id=3,
                    description="Analyze function boundaries and references",
                    tools=["find_function_boundaries", "find_references"],
                    expected_output="Function boundaries and reference locations",
                    dependencies=[2]
                ),
                SubTask(
                    id=4,
                    description="Perform deeper analysis of function behavior",
                    tools=["analyze_function", "find_call_references"],
                    expected_output="Detailed function analysis and call graph",
                    dependencies=[3]
                )
            ])
            
        elif task_type == TaskType.PATTERN_SEARCH:
            # Search for specific patterns in memory
            subtasks.extend([
                SubTask(
                    id=1,
                    description="Identify the target process for scanning",
                    tools=["get_process_info"],
                    expected_output="Process information including PID and name",
                    dependencies=[]
                ),
                SubTask(
                    id=2,
                    description="Get memory regions to scan",
                    tools=["get_memory_regions"],
                    expected_output="List of accessible memory regions",
                    dependencies=[1]
                ),
                SubTask(
                    id=3,
                    description="Perform initial broad scan for the pattern",
                    tools=["scan_all"],
                    expected_output="Initial scan results with potential matches",
                    dependencies=[2]
                ),
                SubTask(
                    id=4,
                    description="Narrow down results with more specific patterns",
                    tools=["aob_scan", "search_string"],
                    expected_output="Refined scan results with exact matches",
                    dependencies=[3]
                ),
                SubTask(
                    id=5,
                    description="Generate signature for the found pattern",
                    tools=["generate_signature"],
                    expected_output="Signature that can be used for future searches",
                    dependencies=[4]
                )
            ])
            
        elif task_type == TaskType.BREAKPOINT_DEBUGGING:
            # Set up debugging with breakpoints
            subtasks.extend([
                SubTask(
                    id=1,
                    description="Identify the target process for debugging",
                    tools=["get_process_info"],
                    expected_output="Process information including PID and name",
                    dependencies=[]
                ),
                SubTask(
                    id=2,
                    description="Locate the function or address to set breakpoint",
                    tools=["get_symbol_address", "disassemble"],
                    expected_output="Address information for breakpoint placement",
                    dependencies=[1]
                ),
                SubTask(
                    id=3,
                    description="Set breakpoint at the identified location",
                    tools=["set_breakpoint"],
                    expected_output="Breakpoint confirmation and hit count",
                    dependencies=[2]
                ),
                SubTask(
                    id=4,
                    description="Monitor breakpoint hits and gather data",
                    tools=["get_breakpoint_hits", "read_memory"],
                    expected_output="Breakpoint hit data and memory snapshots",
                    dependencies=[3]
                ),
                SubTask(
                    id=5,
                    description="Analyze collected data for debugging insights",
                    tools=["analyze_function", "disassemble"],
                    expected_output="Analysis of debugging data and insights",
                    dependencies=[4]
                )
            ])
            
        elif task_type == TaskType.COMPREHENSIVE_ANALYSIS:
            # Comprehensive analysis combining multiple approaches
            subtasks.extend([
                SubTask(
                    id=1,
                    description="Gather initial information about the target",
                    tools=["get_process_info", "enum_modules"],
                    expected_output="Basic process and module information",
                    dependencies=[]
                ),
                SubTask(
                    id=2,
                    description="Map out memory layout and regions",
                    tools=["get_memory_regions"],
                    expected_output="Complete memory region map",
                    dependencies=[1]
                ),
                SubTask(
                    id=3,
                    description="Perform initial scans to identify interesting areas",
                    tools=["scan_all", "aob_scan"],
                    expected_output="Initial scan results highlighting interesting areas",
                    dependencies=[2]
                ),
                SubTask(
                    id=4,
                    description="Analyze identified areas in detail",
                    tools=["disassemble", "analyze_function", "read_memory"],
                    expected_output="Detailed analysis of interesting areas",
                    dependencies=[3]
                ),
                SubTask(
                    id=5,
                    description="Synthesize findings and provide recommendations",
                    tools=["generate_signature", "find_references"],
                    expected_output="Comprehensive analysis report with recommendations",
                    dependencies=[4]
                )
            ])
        
        return subtasks
    
    def select_tools(self, subtask: SubTask) -> List[str]:
        """
        Select appropriate tools for a subtask.
        
        Args:
            subtask: The subtask to select tools for
            
        Returns:
            A list of tool names
        """
        return subtask.tools
    
    def _generate_task_id(self) -> str:
        """
        Generate a unique task ID.
        
        Returns:
            A unique task ID
        """
        import uuid
        return str(uuid.uuid4())