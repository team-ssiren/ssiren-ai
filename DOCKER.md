# Docker 실행 가이드

## 사전 준비

Docker Desktop을 실행한 뒤, AI 레포 루트에서 명령어를 실행합니다.

```bash
cd ssiren-ai
```

처음 실행할 때는 예시 환경변수 파일을 복사합니다.

```bash
cp .env.example .env
```

## 실행

```bash
docker compose up --build
```

백그라운드로 실행하려면:

```bash
docker compose up --build -d
```

## 종료

```bash
docker compose down
```