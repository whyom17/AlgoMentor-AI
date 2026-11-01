"""
Phase 0 seed problems — 10 core-pattern problems covering the most common
Blind-75-aligned patterns. Each has:
  - Brute-force reference solution (Python)
  - Optimal reference solution (Python)
  - Public examples for the UI
  - Constraints text

These MUST pass through the differential test pipeline before the
is_published flag is set to True.

Run: python -m app.problem_ingestion.seed_problems
"""

PROBLEMS: list[dict] = [
    {
        "slug": "two-sum",
        "title": "Two Sum",
        "difficulty": "easy",
        "pattern_family": "hash_map",
        "tags": ["arrays", "hash_map"],
        "description": (
            "Given an array of integers `nums` and an integer `target`, "
            "return the indices of the two numbers such that they add up to `target`.\n\n"
            "You may assume that each input would have exactly one solution, "
            "and you may not use the same element twice.\n\n"
            "You can return the answer in any order."
        ),
        "constraints": "2 ≤ nums.length ≤ 10⁴\n-10⁹ ≤ nums[i] ≤ 10⁹\n-10⁹ ≤ target ≤ 10⁹",
        "examples": [
            {"input": "nums = [2,7,11,15], target = 9", "output": "[0,1]", "explanation": "nums[0] + nums[1] == 9"},
            {"input": "nums = [3,2,4], target = 6", "output": "[1,2]"},
        ],
        "starter_code": {
            "python": "from typing import List\n\nclass Solution:\n    def twoSum(self, nums: List[int], target: int) -> List[int]:\n        pass\n",
            "java": "class Solution {\n    public int[] twoSum(int[] nums, int target) {\n        \n    }\n}\n",
        },
        "brute_force": """
def brute_force(nums, target):
    n = len(nums)
    for i in range(n):
        for j in range(i + 1, n):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
""",
        "optimal": """
def optimal(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
""",
        "test_cases": [
            {"input": "[2,7,11,15]\n9", "expected": "[0,1]", "is_sample": True},
            {"input": "[3,2,4]\n6", "expected": "[1,2]", "is_sample": True},
            {"input": "[3,3]\n6", "expected": "[0,1]"},
            {"input": "[1,2,3,4,5]\n9", "expected": "[3,4]"},
        ],
        "time_limit_ms": 1000,
        "memory_limit_mb": 256,
    },
    {
        "slug": "valid-palindrome",
        "title": "Valid Palindrome",
        "difficulty": "easy",
        "pattern_family": "two_pointer",
        "tags": ["strings", "two_pointer"],
        "description": (
            "A phrase is a palindrome if, after converting all uppercase letters to lowercase "
            "and removing all non-alphanumeric characters, it reads the same forward and backward.\n\n"
            "Given a string `s`, return `true` if it is a palindrome, or `false` otherwise."
        ),
        "constraints": "1 ≤ s.length ≤ 2 × 10⁵\ns consists only of printable ASCII characters.",
        "examples": [
            {"input": 's = "A man, a plan, a canal: Panama"', "output": "true"},
            {"input": 's = "race a car"', "output": "false"},
        ],
        "starter_code": {
            "python": "class Solution:\n    def isPalindrome(self, s: str) -> bool:\n        pass\n",
            "java": "class Solution {\n    public boolean isPalindrome(String s) {\n        \n    }\n}\n",
        },
        "brute_force": """
def brute_force(s):
    filtered = ''.join(c.lower() for c in s if c.isalnum())
    return filtered == filtered[::-1]
""",
        "optimal": """
def optimal(s):
    left, right = 0, len(s) - 1
    while left < right:
        while left < right and not s[left].isalnum():
            left += 1
        while left < right and not s[right].isalnum():
            right -= 1
        if s[left].lower() != s[right].lower():
            return False
        left += 1
        right -= 1
    return True
""",
        "test_cases": [
            {"input": '"A man, a plan, a canal: Panama"', "expected": "true", "is_sample": True},
            {"input": '"race a car"', "expected": "false", "is_sample": True},
            {"input": '" "', "expected": "true"},
            {"input": '"0P"', "expected": "false"},
        ],
        "time_limit_ms": 1000,
        "memory_limit_mb": 256,
    },
    {
        "slug": "binary-search",
        "title": "Binary Search",
        "difficulty": "easy",
        "pattern_family": "binary_search",
        "tags": ["arrays", "binary_search"],
        "description": (
            "Given an array of integers `nums` which is sorted in ascending order, "
            "and an integer `target`, write a function to search `target` in `nums`. "
            "If `target` exists, then return its index. Otherwise, return `-1`.\n\n"
            "You must write an algorithm with `O(log n)` runtime complexity."
        ),
        "constraints": "1 ≤ nums.length ≤ 10⁴\n-10⁴ < nums[i], target < 10⁴\nAll integers in nums are unique.\nnums is sorted in ascending order.",
        "examples": [
            {"input": "nums = [-1,0,3,5,9,12], target = 9", "output": "4"},
            {"input": "nums = [-1,0,3,5,9,12], target = 2", "output": "-1"},
        ],
        "starter_code": {
            "python": "from typing import List\n\nclass Solution:\n    def search(self, nums: List[int], target: int) -> int:\n        pass\n",
        },
        "brute_force": """
def brute_force(nums, target):
    for i, n in enumerate(nums):
        if n == target:
            return i
    return -1
""",
        "optimal": """
def optimal(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
""",
        "test_cases": [
            {"input": "[-1,0,3,5,9,12]\n9", "expected": "4", "is_sample": True},
            {"input": "[-1,0,3,5,9,12]\n2", "expected": "-1", "is_sample": True},
            {"input": "[5]\n5", "expected": "0"},
            {"input": "[5]\n6", "expected": "-1"},
        ],
        "time_limit_ms": 1000,
        "memory_limit_mb": 256,
    },
    {
        "slug": "maximum-subarray",
        "title": "Maximum Subarray",
        "difficulty": "medium",
        "pattern_family": "sliding_window",
        "tags": ["arrays", "dynamic_programming", "sliding_window"],
        "description": (
            "Given an integer array `nums`, find the subarray with the largest sum "
            "and return its sum."
        ),
        "constraints": "1 ≤ nums.length ≤ 10⁵\n-10⁴ ≤ nums[i] ≤ 10⁴",
        "examples": [
            {"input": "nums = [-2,1,-3,4,-1,2,1,-5,4]", "output": "6", "explanation": "[4,-1,2,1] has the largest sum = 6"},
            {"input": "nums = [1]", "output": "1"},
        ],
        "starter_code": {
            "python": "from typing import List\n\nclass Solution:\n    def maxSubArray(self, nums: List[int]) -> int:\n        pass\n",
        },
        "brute_force": """
def brute_force(nums):
    n = len(nums)
    best = float('-inf')
    for i in range(n):
        s = 0
        for j in range(i, n):
            s += nums[j]
            best = max(best, s)
    return best
""",
        "optimal": """
def optimal(nums):
    # Kadane's algorithm
    max_sum = nums[0]
    curr = nums[0]
    for n in nums[1:]:
        curr = max(n, curr + n)
        max_sum = max(max_sum, curr)
    return max_sum
""",
        "test_cases": [
            {"input": "[-2,1,-3,4,-1,2,1,-5,4]", "expected": "6", "is_sample": True},
            {"input": "[1]", "expected": "1", "is_sample": True},
            {"input": "[5,4,-1,7,8]", "expected": "23"},
            {"input": "[-1,-2,-3]", "expected": "-1"},
        ],
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
    },
    {
        "slug": "climbing-stairs",
        "title": "Climbing Stairs",
        "difficulty": "easy",
        "pattern_family": "dynamic_programming_1d",
        "tags": ["dynamic_programming", "math"],
        "description": (
            "You are climbing a staircase. It takes `n` steps to reach the top.\n\n"
            "Each time you can either climb `1` or `2` steps. "
            "In how many distinct ways can you climb to the top?"
        ),
        "constraints": "1 ≤ n ≤ 45",
        "examples": [
            {"input": "n = 2", "output": "2"},
            {"input": "n = 3", "output": "3"},
        ],
        "starter_code": {
            "python": "class Solution:\n    def climbStairs(self, n: int) -> int:\n        pass\n",
        },
        "brute_force": """
def brute_force(n):
    if n <= 2:
        return n
    return brute_force(n - 1) + brute_force(n - 2)
""",
        "optimal": """
def optimal(n):
    if n <= 2:
        return n
    a, b = 1, 2
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b
""",
        "test_cases": [
            {"input": "2", "expected": "2", "is_sample": True},
            {"input": "3", "expected": "3", "is_sample": True},
            {"input": "10", "expected": "89"},
            {"input": "45", "expected": "1836311903"},
        ],
        "time_limit_ms": 1000,
        "memory_limit_mb": 256,
    },
    {
        "slug": "reverse-linked-list",
        "title": "Reverse Linked List",
        "difficulty": "easy",
        "pattern_family": "linked_list",
        "tags": ["linked_list"],
        "description": (
            "Given the head of a singly linked list, reverse the list, and return the reversed list."
        ),
        "constraints": "The number of nodes in the list is the range [0, 5000].\n-5000 ≤ Node.val ≤ 5000",
        "examples": [
            {"input": "head = [1,2,3,4,5]", "output": "[5,4,3,2,1]"},
            {"input": "head = [1,2]", "output": "[2,1]"},
        ],
        "starter_code": {
            "python": "from typing import Optional\n\n# Definition for singly-linked list.\nclass ListNode:\n    def __init__(self, val=0, next=None):\n        self.val = val\n        self.next = next\n\nclass Solution:\n    def reverseList(self, head: Optional[ListNode]) -> Optional[ListNode]:\n        pass\n",
        },
        "brute_force": """
def brute_force(head):
    vals = []
    curr = head
    while curr:
        vals.append(curr.val)
        curr = curr.next
    curr = head
    for v in reversed(vals):
        curr.val = v
        curr = curr.next
    return head
""",
        "optimal": """
def optimal(head):
    prev = None
    curr = head
    while curr:
        nxt = curr.next
        curr.next = prev
        prev = curr
        curr = nxt
    return prev
""",
        "test_cases": [
            {"input": "[1,2,3,4,5]", "expected": "[5,4,3,2,1]", "is_sample": True},
            {"input": "[1,2]", "expected": "[2,1]", "is_sample": True},
            {"input": "[]", "expected": "[]"},
        ],
        "time_limit_ms": 1000,
        "memory_limit_mb": 256,
    },
    {
        "slug": "number-of-islands",
        "title": "Number of Islands",
        "difficulty": "medium",
        "pattern_family": "graph_bfs_dfs",
        "tags": ["graphs", "dfs", "bfs", "matrix"],
        "description": (
            "Given an m × n 2D binary grid `grid` which represents a map of '1's (land) "
            "and '0's (water), return the number of islands.\n\n"
            "An island is surrounded by water and is formed by connecting adjacent lands "
            "horizontally or vertically. You may assume all four edges of the grid are all "
            "surrounded by water."
        ),
        "constraints": "m == grid.length\nn == grid[i].length\n1 ≤ m, n ≤ 300\ngrid[i][j] is '0' or '1'.",
        "examples": [
            {
                "input": 'grid = [["1","1","1","1","0"],["1","1","0","1","0"],["1","1","0","0","0"],["0","0","0","0","0"]]',
                "output": "1",
            },
            {
                "input": 'grid = [["1","1","0","0","0"],["1","1","0","0","0"],["0","0","1","0","0"],["0","0","0","1","1"]]',
                "output": "3",
            },
        ],
        "starter_code": {
            "python": "from typing import List\n\nclass Solution:\n    def numIslands(self, grid: List[List[str]]) -> int:\n        pass\n",
        },
        "brute_force": """
def brute_force(grid):
    # DFS — same asymptotic as optimal, just less clean
    if not grid:
        return 0
    m, n = len(grid), len(grid[0])
    visited = [[False] * n for _ in range(m)]
    count = 0

    def dfs(r, c):
        if r < 0 or r >= m or c < 0 or c >= n or visited[r][c] or grid[r][c] == '0':
            return
        visited[r][c] = True
        for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
            dfs(r+dr, c+dc)

    for r in range(m):
        for c in range(n):
            if not visited[r][c] and grid[r][c] == '1':
                dfs(r, c)
                count += 1
    return count
""",
        "optimal": """
def optimal(grid):
    if not grid:
        return 0
    m, n = len(grid), len(grid[0])
    count = 0

    def sink(r, c):
        if r < 0 or r >= m or c < 0 or c >= n or grid[r][c] != '1':
            return
        grid[r][c] = '0'  # mark visited in-place
        sink(r+1, c); sink(r-1, c); sink(r, c+1); sink(r, c-1)

    for r in range(m):
        for c in range(n):
            if grid[r][c] == '1':
                sink(r, c)
                count += 1
    return count
""",
        "test_cases": [
            {
                "input": '[["1","1","1","1","0"],["1","1","0","1","0"],["1","1","0","0","0"],["0","0","0","0","0"]]',
                "expected": "1",
                "is_sample": True,
            },
            {
                "input": '[["1","1","0","0","0"],["1","1","0","0","0"],["0","0","1","0","0"],["0","0","0","1","1"]]',
                "expected": "3",
                "is_sample": True,
            },
            {"input": '[["1"]]', "expected": "1"},
            {"input": '[["0"]]', "expected": "0"},
        ],
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
    },
    {
        "slug": "merge-intervals",
        "title": "Merge Intervals",
        "difficulty": "medium",
        "pattern_family": "interval",
        "tags": ["arrays", "sorting", "interval"],
        "description": (
            "Given an array of `intervals` where `intervals[i] = [start_i, end_i]`, "
            "merge all overlapping intervals, and return an array of the non-overlapping "
            "intervals that cover all the intervals in the input."
        ),
        "constraints": "1 ≤ intervals.length ≤ 10⁴\nintervals[i].length == 2\n0 ≤ start_i ≤ end_i ≤ 10⁴",
        "examples": [
            {"input": "intervals = [[1,3],[2,6],[8,10],[15,18]]", "output": "[[1,6],[8,10],[15,18]]"},
            {"input": "intervals = [[1,4],[4,5]]", "output": "[[1,5]]"},
        ],
        "starter_code": {
            "python": "from typing import List\n\nclass Solution:\n    def merge(self, intervals: List[List[int]]) -> List[List[int]]:\n        pass\n",
        },
        "brute_force": """
def brute_force(intervals):
    # Repeatedly merge until stable — O(n^2)
    def has_overlap(a, b):
        return a[0] <= b[1] and b[0] <= a[1]
    changed = True
    while changed:
        changed = False
        new_intervals = []
        used = [False] * len(intervals)
        for i in range(len(intervals)):
            if used[i]:
                continue
            merged = intervals[i][:]
            for j in range(i+1, len(intervals)):
                if not used[j] and has_overlap(merged, intervals[j]):
                    merged = [min(merged[0], intervals[j][0]), max(merged[1], intervals[j][1])]
                    used[j] = True
                    changed = True
            new_intervals.append(merged)
        intervals = new_intervals
    return intervals
""",
        "optimal": """
def optimal(intervals):
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
""",
        "test_cases": [
            {"input": "[[1,3],[2,6],[8,10],[15,18]]", "expected": "[[1,6],[8,10],[15,18]]", "is_sample": True},
            {"input": "[[1,4],[4,5]]", "expected": "[[1,5]]", "is_sample": True},
            {"input": "[[1,4],[0,4]]", "expected": "[[0,4]]"},
            {"input": "[[1,4],[2,3]]", "expected": "[[1,4]]"},
        ],
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
    },
    {
        "slug": "daily-temperatures",
        "title": "Daily Temperatures",
        "difficulty": "medium",
        "pattern_family": "monotonic_stack",
        "tags": ["arrays", "stack", "monotonic_stack"],
        "description": (
            "Given an array of integers `temperatures` represents the daily temperatures, "
            "return an array `answer` such that `answer[i]` is the number of days you have to wait "
            "after the `i`th day to get a warmer temperature. "
            "If there is no future day for which this is possible, keep `answer[i] == 0` instead."
        ),
        "constraints": "1 ≤ temperatures.length ≤ 10⁵\n30 ≤ temperatures[i] ≤ 100",
        "examples": [
            {"input": "temperatures = [73,74,75,71,69,72,76,73]", "output": "[1,1,4,2,1,1,0,0]"},
            {"input": "temperatures = [30,40,50,60]", "output": "[1,1,1,0]"},
        ],
        "starter_code": {
            "python": "from typing import List\n\nclass Solution:\n    def dailyTemperatures(self, temperatures: List[int]) -> List[int]:\n        pass\n",
        },
        "brute_force": """
def brute_force(temperatures):
    n = len(temperatures)
    answer = [0] * n
    for i in range(n):
        for j in range(i+1, n):
            if temperatures[j] > temperatures[i]:
                answer[i] = j - i
                break
    return answer
""",
        "optimal": """
def optimal(temperatures):
    n = len(temperatures)
    answer = [0] * n
    stack = []  # monotonically decreasing stack of indices
    for i, temp in enumerate(temperatures):
        while stack and temperatures[stack[-1]] < temp:
            idx = stack.pop()
            answer[idx] = i - idx
        stack.append(i)
    return answer
""",
        "test_cases": [
            {"input": "[73,74,75,71,69,72,76,73]", "expected": "[1,1,4,2,1,1,0,0]", "is_sample": True},
            {"input": "[30,40,50,60]", "expected": "[1,1,1,0]", "is_sample": True},
            {"input": "[30,60,90]", "expected": "[1,1,0]"},
            {"input": "[90,80,70,60]", "expected": "[0,0,0,0]"},
        ],
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
    },
    {
        "slug": "kth-largest-element-in-array",
        "title": "Kth Largest Element in an Array",
        "difficulty": "medium",
        "pattern_family": "heap_priority_queue",
        "tags": ["arrays", "sorting", "heap"],
        "description": (
            "Given an integer array `nums` and an integer `k`, return the `k`th largest element in the array.\n\n"
            "Note that it is the `k`th largest element in the sorted order, not the `k`th distinct element.\n\n"
            "Can you solve it without sorting?"
        ),
        "constraints": "1 ≤ k ≤ nums.length ≤ 10⁵\n-10⁴ ≤ nums[i] ≤ 10⁴",
        "examples": [
            {"input": "nums = [3,2,1,5,6,4], k = 2", "output": "5"},
            {"input": "nums = [3,2,3,1,2,4,5,5,6], k = 4", "output": "4"},
        ],
        "starter_code": {
            "python": "from typing import List\n\nclass Solution:\n    def findKthLargest(self, nums: List[int], k: int) -> int:\n        pass\n",
        },
        "brute_force": """
def brute_force(nums, k):
    return sorted(nums, reverse=True)[k - 1]
""",
        "optimal": """
import heapq
def optimal(nums, k):
    # Min-heap of size k
    heap = []
    for num in nums:
        heapq.heappush(heap, num)
        if len(heap) > k:
            heapq.heappop(heap)
    return heap[0]
""",
        "test_cases": [
            {"input": "[3,2,1,5,6,4]\n2", "expected": "5", "is_sample": True},
            {"input": "[3,2,3,1,2,4,5,5,6]\n4", "expected": "4", "is_sample": True},
            {"input": "[1]\n1", "expected": "1"},
            {"input": "[-1,-1]\n1", "expected": "-1"},
        ],
        "time_limit_ms": 2000,
        "memory_limit_mb": 256,
    },
]
