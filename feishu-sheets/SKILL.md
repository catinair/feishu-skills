---
name: feishu-sheets
version: 1.1.0
description: |
  飞书电子表格技能：创建表格、读取/写入/追加单元格、导出 CSV。
  纯 Python 标准库（Pillow 可选，用于画板图片裁剪）。
metadata:
  requires:
    bins: ["python3"]
    files: ["feishu-sheets/sheet_create.py", "feishu-sheets/sheet_info.py", "feishu-sheets/sheet_read.py", "feishu-sheets/sheet_write.py", "feishu-sheets/sheet_append.py", "feishu-sheets/sheet_export_csv.py", "config/credentials.json"]
---

# feishu-sheets -- 飞书电子表格技能

## 权限要求

| 脚本 | 所需权限 | 状态 |
|------|---------|------|
| sheet_create.py | `sheets:spreadsheet` / `sheets:spreadsheet:create` | 已开通 |
| sheet_info.py | `sheets:spreadsheet` | 已开通 |
| sheet_read.py | `sheets:spreadsheet` | 已开通 |
| sheet_write.py | `sheets:spreadsheet` | 已开通 |
| sheet_append.py | `sheets:spreadsheet` | 已开通 |
| sheet_export_csv.py | `docs:document:export` / `drive:file:download` | **需申请** |

## 输出说明

本模块的写操作类 CLI（如创建、更新、删除等）默认输出精简摘要，便于 AI 消费。如需完整 API 原始响应，请加 `--raw`：

```bash
python3 feishu-sheets/sheet_write.py --app sheet_token --range A1:B2 --values "[[1,2],[3,4]]" --raw
```

通用 CLI 约定（`--yes`、`--raw`、`--identity`）详见项目级文档 [`docs/usage.md`](../docs/usage.md)。

## 快捷命令

### 创建表格

```bash
python3 feishu-sheets/sheet_create.py --title "销售数据"
```

默认创建到指定文件夹，可通过 `--folder-token` 自定义位置。

### 获取表格元数据

```bash
python3 feishu-sheets/sheet_info.py --token shtcnxxx
```

返回 sheet_id、行列数等信息。sheet_id 用于后续读写操作。

### 读取单元格

```bash
python3 feishu-sheets/sheet_read.py --token shtcnxxx --sheet 5e0aa6 --range A1:B10
```

### 写入单元格

```bash
python3 feishu-sheets/sheet_write.py \
  --token shtcnxxx \
  --sheet 5e0aa6 \
  --range A1:B2 \
  --values '[["姓名","年龄"],["张三",25]]'
```

### 追加行

```bash
python3 feishu-sheets/sheet_append.py \
  --token shtcnxxx \
  --sheet 5e0aa6 \
  --values '[["李四",30]]'
```

追加会自动在表格末尾插入新行，不会覆盖已有数据。

### 导出为 CSV

```bash
# 导出默认 sheet 为 CSV
python3 feishu-sheets/sheet_export_csv.py --token shtcnxxx --output ./sheet.csv

# 导出指定 sheet 为 CSV
python3 feishu-sheets/sheet_export_csv.py --token shtcnxxx --sheet-id 0edxxx --output ./sheet.csv

# 从 URL 自动提取 token
python3 feishu-sheets/sheet_export_csv.py \
  --url "https://xxx.feishu.cn/sheets/shtcnxxx" \
  --output ./sheet.csv
```

**注意**：
- 不指定 `--sheet-id` 时自动导出第一个 sheet
- CSV 是纯文本格式，AI 可直接读取
- 需开通 `docs:document:export` 权限

## 工作流程

```
1. sheet_create.py --title "xxx"          → 获取 spreadsheet_token
2. sheet_info.py --token xxx              → 获取 sheet_id
3. sheet_write.py --token xxx --sheet yyy → 写入表头
4. sheet_append.py --token xxx --sheet yyy → 追加数据行
```

## 注意事项

- `sheet_id` 不是 `0` 或 `1`，而是类似 `5e0aa6` 的字符串，需通过 `sheet_info.py` 获取
- `--values` 参数是 JSON 格式的二维数组
- 追加操作不会覆盖已有数据，始终在末尾插入新行
