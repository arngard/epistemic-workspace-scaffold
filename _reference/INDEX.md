---
date created: 2026-05-03
date modified: 2026-05-03
tags: [reference]
---

# `_reference/` 색인

사용자가 임의로 dump하는 raw 자료의 immutable 보관 영역. 형태 무관 (PDF, 이미지, 텍스트 메모, URL 모음, 기사 클리핑, 스크린샷 등).

## 운용 원칙

- 처리 후에도 이 폴더의 파일은 삭제·수정하지 않는다. derived 노드(`_docs/_*` 하위)에서 `cf. _reference/<file>` 형태로 reference만 남긴다.
- 본 INDEX는 폴더 내용의 인벤토리이자 처리 진척의 SSOT다. 새 파일이 추가되면 본 INDEX에 등재하고, 통합·처리 후 상태 컬럼을 갱신한다.
- AI는 새 세션 시작 시 본 INDEX와 폴더 실제 내용을 대조한다. 폴더에는 있지만 INDEX에 없으면 신규 미처리 자료다 (등재하고 처리 절차 시작). INDEX에는 있지만 폴더에 없으면 raw 자료가 사라졌다는 뜻이며, 사용자에게 짚는다.
- 자세한 처리 절차: [`../_docs/_architecture/ingest-workflow.md`](../_docs/_architecture/ingest-workflow.md) "`_reference/` 폴더 처리" 섹션.

## 처리 상태 표기

상태 컬럼에 다음 중 하나를 적는다.

- `처리 대기`: 등재됐지만 derived 노드로 통합되지 않음.
- `처리됨`: derived 노드로 통합 완료. 같은 행에 derived 노드 링크를 함께 적는다.
- `사용자 의견 필요`: 처리 방향이 모호해 사용자 확인 대기.
- `보관용`: 즉각 통합 대상이 아니지만 추후 참조 가능성을 위해 보관.

## 등록된 자료

| 파일 | 추가일 | 설명 | 상태 |
|------|--------|------|------|

(아직 등록된 자료 없음.)
