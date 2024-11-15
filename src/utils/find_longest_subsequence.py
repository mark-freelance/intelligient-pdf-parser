from typing import List
from src.log import logger

def find_longest_subsequence(sequence: List[int], debug=False) -> List[int]:
    """
    sequence 是一个递增序列，查找其中的最长子串，比如 [2,3,5,6,7,9] --> [5,6,7]，并返回它的序号列表，即 [2,3,4]
    只有一个数时，返回自身
    类似 [89, 91] 这种，都一样，取最后一个满足条件的，也就是 [1]
    """
    if debug: logger.info(f'sequence: {sequence}')
    if not sequence:
        return []

    if len(sequence) == 1:
        return [0]

    # Find all consecutive subsequences
    subsequences = []
    current = [0]  # Start with first index

    for i in range(1, len(sequence)):
        if sequence[i] == sequence[i-1] + 1:
            current.append(i)
        else:
            if len(current) > 1:  # Only keep subsequences of length > 1
                subsequences.append(current)
            current = [i]

    if len(current) > 1:  # Handle the last subsequence
        subsequences.append(current)
    
    if debug: logger.info(f'longest subsequence: {subsequences}')

    # If no consecutive subsequences found, return the last index
    if not subsequences:
        return [len(sequence) - 1]

    # Return the longest subsequence
    answer = max(subsequences, key=len)
    if debug: logger.info(f'answer: {answer}')
    return answer


if __name__ == '__main__':
    assert find_longest_subsequence([2,3,5,6,7,9], True) == [2,3,4]
    assert find_longest_subsequence([], True) == []
    assert find_longest_subsequence([89], True) == [0]
    assert find_longest_subsequence([89, 91], True) == [1]