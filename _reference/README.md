# `_reference/`

사용자가 임의로 dump하는 raw 자료의 immutable 보관 영역.

## 사용

여기에 PDF·이미지·텍스트 메모·URL 모음·기사 클리핑·스크린샷 등 어떤 형태의 자료든 넣을 수 있다. AI는 새 세션 시작 시 또는 작업 중 트리거에 따라 처리되지 않은 항목을 감지하고, 적절한 derived 노드(`_docs/` 하위)에 통합하거나 사용자에게 처리 방향을 묻는다.

## 처리 여부 판정

별도 처리 로그 파일은 두지 않는다. 본문 어디든 그 파일 경로(`_reference/<file>`)를 reference로 적었는지를 SSOT로 본다. AI는 `_reference/` 내용을 listing한 뒤, 각 파일 경로를 워크스페이스 본문에서 grep해 미처리 여부를 판정한다.

## 파일은 immutable

처리 후에도 이 폴더의 파일은 삭제·수정하지 않는다. derived 노드에 `cf. _reference/<file>` 형태로 reference만 남긴다. derived 노드가 변경되더라도 raw 입력으로 항상 되돌아갈 수 있어야 한다.

## 자세한 절차

[`../_docs/_architecture/ingest-workflow.md`](../_docs/_architecture/ingest-workflow.md) "`_reference/` 폴더 처리" 섹션 참조.
