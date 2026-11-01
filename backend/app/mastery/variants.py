"""
Isomorphic problem variant map.

AGENTS.md constraint #6: spaced repetition must serve isomorphic variants,
not the same problem. This file is the authoritative mapping from pattern
family to problem slugs within that family.

Structure:
  {
    "pattern_family": {
      "description": "...",
      "problems": ["slug1", "slug2", "slug3"],  # ordered by difficulty
    }
  }
"""

VARIANT_MAP: dict[str, dict] = {
    "sliding_window": {
        "description": "Maintain a window of elements satisfying a constraint.",
        "problems": [
            "maximum-subarray",           # easy — classic Kadane / sliding window intro
            "longest-substring-without-repeating-characters",  # medium
            "minimum-window-substring",   # hard
        ],
    },
    "two_pointer": {
        "description": "Use two indices moving toward each other or in tandem.",
        "problems": [
            "valid-palindrome",
            "two-sum-ii-sorted",
            "three-sum",
            "container-with-most-water",
        ],
    },
    "binary_search": {
        "description": "Divide and conquer on a sorted/monotonic search space.",
        "problems": [
            "binary-search",
            "find-minimum-in-rotated-sorted-array",
            "search-in-rotated-sorted-array",
            "median-of-two-sorted-arrays",
        ],
    },
    "dynamic_programming_1d": {
        "description": "1-D DP: build up a solution from smaller subproblems.",
        "problems": [
            "climbing-stairs",
            "house-robber",
            "longest-increasing-subsequence",
            "coin-change",
            "word-break",
        ],
    },
    "dynamic_programming_2d": {
        "description": "2-D DP on grids or string pairs.",
        "problems": [
            "unique-paths",
            "longest-common-subsequence",
            "edit-distance",
        ],
    },
    "graph_bfs_dfs": {
        "description": "Graph traversal — BFS for shortest paths, DFS for exploration.",
        "problems": [
            "number-of-islands",
            "clone-graph",
            "pacific-atlantic-water-flow",
            "word-ladder",
        ],
    },
    "tree_traversal": {
        "description": "Binary tree DFS/BFS patterns.",
        "problems": [
            "invert-binary-tree",
            "maximum-depth-of-binary-tree",
            "binary-tree-level-order-traversal",
            "lowest-common-ancestor",
            "binary-tree-right-side-view",
        ],
    },
    "monotonic_stack": {
        "description": "Maintain a monotonically increasing/decreasing stack.",
        "problems": [
            "daily-temperatures",
            "next-greater-element-i",
            "largest-rectangle-in-histogram",
        ],
    },
    "heap_priority_queue": {
        "description": "Min/max heap for k-th element or streaming problems.",
        "problems": [
            "kth-largest-element-in-array",
            "top-k-frequent-elements",
            "find-median-from-data-stream",
        ],
    },
    "backtracking": {
        "description": "Explore all options, prune invalid paths.",
        "problems": [
            "subsets",
            "permutations",
            "combination-sum",
            "word-search",
            "n-queens",
        ],
    },
    "hash_map": {
        "description": "Use a hash map for O(1) lookup / frequency counting.",
        "problems": [
            "two-sum",
            "group-anagrams",
            "longest-consecutive-sequence",
        ],
    },
    "linked_list": {
        "description": "Pointer manipulation on singly/doubly linked lists.",
        "problems": [
            "reverse-linked-list",
            "linked-list-cycle",
            "merge-two-sorted-lists",
            "reorder-list",
            "lru-cache",
        ],
    },
    "interval": {
        "description": "Sort-based interval merging / scheduling.",
        "problems": [
            "merge-intervals",
            "insert-interval",
            "meeting-rooms",
            "non-overlapping-intervals",
        ],
    },
    "trie": {
        "description": "Prefix tree for string search problems.",
        "problems": [
            "implement-trie",
            "word-search-ii",
            "design-add-and-search-words",
        ],
    },
}


def get_variants_for_pattern(pattern_family: str) -> list[str]:
    """Return the list of problem slugs for a pattern family."""
    entry = VARIANT_MAP.get(pattern_family)
    if not entry:
        return []
    return entry["problems"]


def get_next_variant(
    pattern_family: str, solved_slugs: set[str]
) -> str | None:
    """
    Return the next unsolved variant in the pattern family,
    or None if all are solved.
    """
    variants = get_variants_for_pattern(pattern_family)
    for slug in variants:
        if slug not in solved_slugs:
            return slug
    return None
