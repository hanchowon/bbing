"""
==============================================================================
알고리즘 시각화 백엔드 서버 (Google Cloud Run용)
- 지원 알고리즘: 셸 정렬(Shell Sort), 퀵 정렬(Quick Sort), 병합 정렬(Merge Sort)
- 역할: 단순히 정렬 결과만 반환하지 않고, 각 알고리즘 고유의 중간 동작 과정을
       '상태 스냅샷(State Snapshot)'으로 상세히 기록하여 히스토리 로그로 클라이언트에 제공합니다.
==============================================================================
"""

import os
import random
from typing import Any, Dict, List, Optional
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)

# Cloud Run 배포 및 웹 클라이언트(GAS, 로컬 HTML)에서의 원활한 호출을 위한 CORS 전체 허용
CORS(app, resources={r"/*": {"origins": "*"}})


# ============================================================================
# 스냅샷 헬퍼 클래스 및 함수
# ============================================================================
class SnapshotRecorder:
    """
    정렬 알고리즘 실행 도중 발생하는 매 단계의 배열 상태 및 메타데이터를 기록하는 클래스
    """
    def __init__(self, initial_array: List[int], algorithm_name: str):
        self.algorithm_name = algorithm_name
        self.snapshots: List[Dict[str, Any]] = []
        self.step_counter = 0
        self.sorted_indices: set = set()

        # 최초 시작 상태 기록
        self.record(
            current_array=initial_array,
            action="init",
            description=f"[{algorithm_name}] 초기 배열 상태입니다.",
            comparing=[],
            swapping=[],
            pivot=None,
            range_bounds=None,
            metadata={}
        )

    def record(
        self,
        current_array: List[int],
        action: str,
        description: str,
        comparing: Optional[List[int]] = None,
        swapping: Optional[List[int]] = None,
        pivot: Optional[int] = None,
        range_bounds: Optional[List[int]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        한 번의 동작에 대한 스냅샷을 생성하여 히스토리에 추가합니다.
        """
        self.step_counter += 1
        snapshot = {
            "step": self.step_counter,
            "array": list(current_array),  # 깊은 복사로 현재 시점의 배열 값 보존
            "action": action,
            "description": description,
            "indices": {
                "comparing": comparing if comparing is not None else [],
                "swapping": swapping if swapping is not None else [],
                "pivot": pivot,
                "range": range_bounds,
                "sorted": sorted(list(self.sorted_indices))
            },
            "metadata": metadata if metadata is not None else {}
        }
        self.snapshots.append(snapshot)


# ============================================================================
# 1. 셸 정렬 (Shell Sort)
# - 간격(Gap) 크기 변화
# - 설정된 간격만큼 떨어진 요소들 간의 그룹화 및 비교
# - 삽입(교환)되어 가는 상태 기록
# ============================================================================
def record_shell_sort(arr: List[int]) -> Dict[str, Any]:
    work_arr = list(arr)
    n = len(work_arr)
    recorder = SnapshotRecorder(work_arr, "셸 정렬")

    gap = n // 2
    while gap > 0:
        # 1) 간격(Gap)의 크기 변화 기록
        recorder.record(
            current_array=work_arr,
            action="gap_change",
            description=f"간격(Gap)을 {gap}으로 설정했습니다. 이 간격으로 부분 배열들을 구성합니다.",
            metadata={"gap": gap}
        )

        # 2) 설정된 간격만큼 떨어진 요소들에 대한 삽입 정렬 수행
        for i in range(gap, n):
            temp = work_arr[i]
            j = i

            # 비교 시작 스냅샷
            recorder.record(
                current_array=work_arr,
                action="compare",
                description=f"간격 {gap} 기준 비교: 인덱스 {j - gap}(값: {work_arr[j - gap]})와 인덱스 {j}(값: {temp})를 비교합니다.",
                comparing=[j - gap, j],
                metadata={"gap": gap, "insert_value": temp}
            )

            while j >= gap and work_arr[j - gap] > temp:
                # 앞쪽의 큰 요소를 뒤로 이동 (Shift / Swap)
                work_arr[j] = work_arr[j - gap]
                recorder.record(
                    current_array=work_arr,
                    action="swap",
                    description=f"{work_arr[j - gap]}이(가) 삽입할 값 {temp}보다 크므로 인덱스 {j - gap}에서 인덱스 {j} 위치로 이동합니다.",
                    swapping=[j - gap, j],
                    metadata={"gap": gap, "moved_value": work_arr[j]}
                )
                j -= gap

                if j >= gap:
                    recorder.record(
                        current_array=work_arr,
                        action="compare",
                        description=f"간격 {gap}만큼 이전 요소와 계속 비교: 인덱스 {j - gap}(값: {work_arr[j - gap]}) vs 임시값 {temp}",
                        comparing=[j - gap, j],
                        metadata={"gap": gap, "insert_value": temp}
                    )

            # 알맞은 위치에 temp 삽입
            work_arr[j] = temp
            recorder.record(
                current_array=work_arr,
                action="insert",
                description=f"적절한 위치를 찾아 값 {temp}을 인덱스 {j}에 삽입(배치)했습니다.",
                swapping=[j],
                metadata={"gap": gap, "inserted_index": j, "value": temp}
            )

        gap //= 2

    # 정렬 완료 상태 표시
    recorder.sorted_indices = set(range(n))
    recorder.record(
        current_array=work_arr,
        action="complete",
        description="셸 정렬이 모두 완료되었습니다. 모든 요소가 오름차순으로 정렬되었습니다.",
        metadata={"total_steps": recorder.step_counter}
    )

    return {
        "algorithm": "shell_sort",
        "name": "셸 정렬 (Shell Sort)",
        "complexity": {
            "best": "O(n log n)",
            "average": "O(n^1.25) ~ O(n^1.5)",
            "worst": "O(n^2)",
            "space": "O(1)"
        },
        "description": "삽입 정렬의 장점을 살리고 단점을 보완한 알고리즘으로, 일정 간격(Gap)만큼 떨어진 요소들을 먼저 정렬한 후 점차 간격을 줄여나갑니다.",
        "snapshots": recorder.snapshots,
        "total_steps": len(recorder.snapshots),
        "final_array": work_arr
    }


# ============================================================================
# 2. 퀵 정렬 (Quick Sort)
# - 피벗(Pivot) 지정
# - 피벗과의 대소 비교 대상
# - 요소 교환 위치
# - 피벗의 최종 정렬 확정 상태 기록
# ============================================================================
def record_quick_sort(arr: List[int]) -> Dict[str, Any]:
    work_arr = list(arr)
    n = len(work_arr)
    recorder = SnapshotRecorder(work_arr, "퀵 정렬")

    def quick_sort_recursive(low: int, high: int):
        if low > high:
            return
        if low == high:
            recorder.sorted_indices.add(low)
            recorder.record(
                current_array=work_arr,
                action="pivot_fixed",
                description=f"단일 요소 구간 [{low}]이므로 인덱스 {low}(값: {work_arr[low]})의 정렬 위치가 확정되었습니다.",
                range_bounds=[low, high],
                metadata={"fixed_index": low}
            )
            return

        # 1) 피벗(Pivot) 지정 (가장 오른쪽 요소를 피벗으로 선택)
        pivot = work_arr[high]
        recorder.record(
            current_array=work_arr,
            action="pivot_select",
            description=f"구간 [{low}..{high}]에서 피벗으로 인덱스 {high}(값: {pivot})를 지정했습니다.",
            pivot=high,
            range_bounds=[low, high],
            metadata={"pivot_value": pivot, "pivot_index": high}
        )

        i = low - 1  # 피벗보다 작은 요소들이 위치할 경계선 인덱스
        for j in range(low, high):
            # 2) 피벗과의 대소 비교
            recorder.record(
                current_array=work_arr,
                action="compare",
                description=f"피벗({pivot})과 인덱스 {j}(값: {work_arr[j]}) 비교 중...",
                comparing=[j, high],
                pivot=high,
                range_bounds=[low, high],
                metadata={"pivot_value": pivot}
            )

            if work_arr[j] < pivot:
                i += 1
                if i != j:
                    # 3) 요소 교환 위치 기록
                    work_arr[i], work_arr[j] = work_arr[j], work_arr[i]
                    recorder.record(
                        current_array=work_arr,
                        action="swap",
                        description=f"값 {work_arr[i]}이(가) 피벗({pivot})보다 작으므로 인덱스 {i}와 {j}의 위치를 교환합니다.",
                        swapping=[i, j],
                        pivot=high,
                        range_bounds=[low, high]
                    )

        # 피벗을 제자리(i + 1)로 이동하여 분할 완료
        fixed_pivot_idx = i + 1
        work_arr[fixed_pivot_idx], work_arr[high] = work_arr[high], work_arr[fixed_pivot_idx]

        # 4) 피벗의 최종 정렬 확정 상태 기록
        recorder.sorted_indices.add(fixed_pivot_idx)
        recorder.record(
            current_array=work_arr,
            action="pivot_fixed",
            description=f"피벗 {pivot}이 최종 정렬 위치인 인덱스 {fixed_pivot_idx}로 이동되어 확정되었습니다.",
            swapping=[fixed_pivot_idx, high] if fixed_pivot_idx != high else [],
            pivot=fixed_pivot_idx,
            range_bounds=[low, high],
            metadata={"fixed_pivot": fixed_pivot_idx, "value": pivot}
        )

        # 재귀 호출: 피벗 기준 좌측/우측 부분 배열 정렬
        quick_sort_recursive(low, fixed_pivot_idx - 1)
        quick_sort_recursive(fixed_pivot_idx + 1, high)

    quick_sort_recursive(0, n - 1)

    recorder.sorted_indices = set(range(n))
    recorder.record(
        current_array=work_arr,
        action="complete",
        description="퀵 정렬이 완료되었습니다. 모든 피벗이 제자리를 찾았습니다.",
        metadata={"total_steps": recorder.step_counter}
    )

    return {
        "algorithm": "quick_sort",
        "name": "퀵 정렬 (Quick Sort)",
        "complexity": {
            "best": "O(n log n)",
            "average": "O(n log n)",
            "worst": "O(n^2)",
            "space": "O(log n)"
        },
        "description": "기준이 되는 피벗(Pivot)을 설정하여 피벗보다 작은 값과 큰 값으로 분할하며 정복하는 대표적인 분할 정복(Divide & Conquer) 알고리즘입니다.",
        "snapshots": recorder.snapshots,
        "total_steps": len(recorder.snapshots),
        "final_array": work_arr
    }


# ============================================================================
# 3. 병합 정렬 (Merge Sort)
# - 배열이 논리적으로 분할되는 구간 (Divide)
# - 두 부분 배열을 병합하며 좌우 요소를 비교하는 과정
# - 임시 배열에서 정렬 완료된 후 원본 배열로 덮어씌워지는(Overwrite) 상태 기록
# ============================================================================
def record_merge_sort(arr: List[int]) -> Dict[str, Any]:
    work_arr = list(arr)
    n = len(work_arr)
    recorder = SnapshotRecorder(work_arr, "병합 정렬")

    def merge(left: int, mid: int, right: int):
        # 2) 두 부분 배열 병합 시작
        recorder.record(
            current_array=work_arr,
            action="merge_start",
            description=f"부분배열 [{left}..{mid}]와 [{mid + 1}..{right}]의 병합을 시작합니다.",
            range_bounds=[left, right],
            metadata={"left_range": [left, mid], "right_range": [mid + 1, right]}
        )

        temp: List[int] = []
        i = left
        j = mid + 1

        while i <= mid and j <= right:
            # 좌우 요소 비교 스냅샷
            recorder.record(
                current_array=work_arr,
                action="merge_compare",
                description=f"좌측 인덱스 {i}(값: {work_arr[i]}) vs 우측 인덱스 {j}(값: {work_arr[j]}) 비교 중...",
                comparing=[i, j],
                range_bounds=[left, right]
            )

            if work_arr[i] <= work_arr[j]:
                temp.append(work_arr[i])
                i += 1
            else:
                temp.append(work_arr[j])
                j += 1

        while i <= mid:
            temp.append(work_arr[i])
            i += 1

        while j <= right:
            temp.append(work_arr[j])
            j += 1

        # 3) 임시 배열에서 정렬 완료 후 원본 배열로 덮어씌우는(Overwrite) 상태를 요소별로 기록
        for idx, val in enumerate(temp):
            target_idx = left + idx
            work_arr[target_idx] = val
            recorder.record(
                current_array=work_arr,
                action="merge_overwrite",
                description=f"정렬된 값 {val}을 원본 배열 인덱스 {target_idx}에 덮어씌웁니다(Overwrite).",
                swapping=[target_idx],
                range_bounds=[left, right],
                metadata={"overwritten_index": target_idx, "value": val}
            )

        # 전체 배열이 최종 병합된 경우 정렬 확정 표시
        if left == 0 and right == n - 1:
            recorder.sorted_indices = set(range(n))

    def merge_sort_recursive(left: int, right: int):
        if left >= right:
            return

        mid = (left + right) // 2

        # 1) 배열이 논리적으로 분할되는 구간 기록
        recorder.record(
            current_array=work_arr,
            action="divide",
            description=f"구간 [{left}..{right}]를 좌측 [{left}..{mid}]와 우측 [{mid + 1}..{right}]로 분할합니다.",
            range_bounds=[left, right],
            metadata={"split_mid": mid}
        )

        merge_sort_recursive(left, mid)
        merge_sort_recursive(mid + 1, right)
        merge(left, mid, right)

    merge_sort_recursive(0, n - 1)

    recorder.sorted_indices = set(range(n))
    recorder.record(
        current_array=work_arr,
        action="complete",
        description="병합 정렬이 모두 완료되었습니다. 모든 분할 구간이 성공적으로 병합되었습니다.",
        metadata={"total_steps": recorder.step_counter}
    )

    return {
        "algorithm": "merge_sort",
        "name": "병합 정렬 (Merge Sort)",
        "complexity": {
            "best": "O(n log n)",
            "average": "O(n log n)",
            "worst": "O(n log n)",
            "space": "O(n)"
        },
        "description": "문제를 절반으로 분할한 후 각각 정렬하고, 두 정렬된 부분 배열을 임시 공간을 활용해 하나로 병합하는 안정 정렬(Stable Sort) 알고리즘입니다.",
        "snapshots": recorder.snapshots,
        "total_steps": len(recorder.snapshots),
        "final_array": work_arr
    }


# ============================================================================
# API 라우트 정의
# ============================================================================

@app.route("/", methods=["GET"])
@app.route("/health", methods=["GET"])
def health_check():
    """
    서버 상태 확인용 헬스체크 엔드포인트 (Google Cloud Run 및 클라이언트 공통)
    """
    return jsonify({
        "status": "healthy",
        "service": "quick_sort-algorithm-visualizer-server",
        "version": "1.0.0",
        "supported_algorithms": ["shell_sort", "quick_sort", "merge_sort"],
        "message": "서버가 정상적으로 동작 중입니다."
    }), 200


@app.route("/sort", methods=["POST", "OPTIONS"])
def handle_sort():
    """
    정렬 시뮬레이션 API
    요청 본문(JSON):
      {
        "array": [10, 4, 32, 18, 55, ...] (생략 시 기본 무작위 15개 정수 생성)
      }
    반환:
      3가지 알고리즘(셸 정렬, 퀵 정렬, 병합 정렬)의 전체 상태 스냅샷 히스토리
    """
    if request.method == "OPTIONS":
        return "", 204

    try:
        data = request.get_json(silent=True) or {}
        raw_array = data.get("array")

        if raw_array is None or not isinstance(raw_array, list) or len(raw_array) == 0:
            # 클라이언트에서 배열을 주지 않았을 경우 15개의 기본 무작위 배열 생성 (10 ~ 99)
            raw_array = random.sample(range(10, 100), 14)
        else:
            # 유효성 검사: 정수 여부 확인
            cleaned_array = []
            for item in raw_array:
                try:
                    cleaned_array.append(int(item))
                except (ValueError, TypeError):
                    return jsonify({
                        "success": False,
                        "error": f"잘못된 배열 요소: '{item}'. 모든 요소는 정수여야 합니다."
                    }), 400
            raw_array = cleaned_array

        if len(raw_array) < 2:
            return jsonify({
                "success": False,
                "error": "정렬을 수행하기 위해서는 최소 2개 이상의 요소가 필요합니다."
            }), 400

        if len(raw_array) > 50:
            return jsonify({
                "success": False,
                "error": "시각화 성능 및 부하 방지를 위해 배열 크기는 최대 50개까지 허용됩니다."
            }), 400

        # 세 가지 알고리즘의 스냅샷 생성 실행
        shell_result = record_shell_sort(raw_array)
        quick_result = record_quick_sort(raw_array)
        merge_result = record_merge_sort(raw_array)

        # 세 알고리즘 중 가장 긴 스텝 수 계산 (단일 통합 타임라인 재생용)
        max_steps = max(
            shell_result["total_steps"],
            quick_result["total_steps"],
            merge_result["total_steps"]
        )

        return jsonify({
            "success": True,
            "original_array": raw_array,
            "max_steps": max_steps,
            "algorithms": {
                "shell_sort": shell_result,
                "quick_sort": quick_result,
                "merge_sort": merge_result
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"서버 내부 처리 중 오류가 발생했습니다: {str(e)}"
        }), 500


if __name__ == "__main__":
    # 로컬 개발 및 테스트 실행 (Cloud Run 환경에서는 gunicorn이 진입점으로 동작)
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 정렬 알고리즘 시각화 서버 시작: http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)

