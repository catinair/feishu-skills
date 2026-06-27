#!/usr/bin/env python3
"""Tests for runtime config path resolver in _config_loader."""

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import feishu_common._config_loader as loader


class TestConfigDirResolver(unittest.TestCase):
    def test_local_default_returns_skill_root_config(self):
        """无环境变量、非平台时返回 skill-root/config。"""
        # 当前测试运行在本地，不应被识别为平台
        self.assertIsNone(loader.get_runtime_config_dir())
        config_dir = loader.get_config_dir()
        self.assertEqual(config_dir, loader.SKILL_ROOT / "config")

    def test_env_override_takes_priority(self):
        """FEISHU_CONFIG_DIR 覆盖所有其他路径。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.environ.pop(loader.FEISHU_CONFIG_DIR_ENV, None)
            try:
                os.environ[loader.FEISHU_CONFIG_DIR_ENV] = tmpdir
                self.assertEqual(loader.get_config_dir(), Path(tmpdir))
                self.assertEqual(
                    loader.resolve_config_path("credentials.json"),
                    Path(tmpdir) / "credentials.json",
                )
            finally:
                if old is None:
                    os.environ.pop(loader.FEISHU_CONFIG_DIR_ENV, None)
                else:
                    os.environ[loader.FEISHU_CONFIG_DIR_ENV] = old

    def test_resolve_read_uses_module_constant(self):
        """本地读取路径使用模块级常量（保持测试 patch 兼容）。"""
        path = loader.resolve_config_path("risk_policy.json")
        self.assertEqual(path, loader.RISK_POLICY_FILE)
        self.assertEqual(path, loader.SKILL_ROOT / "config" / "risk_policy.json")


class TestPlatformDetection(unittest.TestCase):
    def test_local_skill_root_not_detected_as_platform(self):
        """当前真实 skill 根目录不应被误判为平台。"""
        # 真实项目路径大概率不是 /home/user/workspace/skills/feishu-skills
        self.assertIsNone(loader._detect_platform_workspace())
        self.assertIsNone(loader.get_runtime_config_dir())

    def test_platform_workspace_detection(self):
        """模拟平台 workspace/skills/<skill>/ 结构时识别为平台。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            skill_root = workspace / "skills" / "feishu-skills"
            skill_root.mkdir(parents=True)
            runtime_dir = workspace / "runtime_credentials" / "feishu-skills"

            original_skill_root = loader.SKILL_ROOT
            original_detect = loader._detect_platform_workspace
            try:
                loader.SKILL_ROOT = skill_root
                loader._detect_platform_workspace = lambda: workspace
                # 清空模块常量缓存
                loader.CONFIG_DIR = loader._compute_default_config_path("")
                loader.CREDENTIALS_FILE = loader._compute_default_config_path("credentials.json")
                loader.SETTINGS_FILE = loader._compute_default_config_path("settings.json")
                loader.PERMISSIONS_FILE = loader._compute_default_config_path("permissions.json")
                loader.RISK_POLICY_FILE = loader._compute_default_config_path("risk_policy.json")

                runtime = loader.get_runtime_config_dir()
                self.assertIsNotNone(runtime)
                self.assertEqual(runtime, runtime_dir)

                # for_write=True 应自动创建 runtime_credentials 目录
                write_dir = loader.get_config_dir(for_write=True)
                self.assertTrue(write_dir.exists())
                self.assertEqual(write_dir, runtime_dir)

                # 写入应落到 runtime_credentials
                write_path = loader.resolve_config_path("credentials.json", for_write=True)
                self.assertEqual(write_path, runtime_dir / "credentials.json")
            finally:
                loader.SKILL_ROOT = original_skill_root
                loader._detect_platform_workspace = original_detect
                loader.CONFIG_DIR = loader._compute_default_config_path("")
                loader.CREDENTIALS_FILE = loader._compute_default_config_path("credentials.json")
                loader.SETTINGS_FILE = loader._compute_default_config_path("settings.json")
                loader.PERMISSIONS_FILE = loader._compute_default_config_path("permissions.json")
                loader.RISK_POLICY_FILE = loader._compute_default_config_path("risk_policy.json")


class TestSafeWriteJson(unittest.TestCase):
    def test_atomic_write_and_permissions(self):
        """safe_write_json 应写入文件并设置 600 权限（credentials 场景）。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "credentials.json"
            loader.safe_write_json(path, {"appId": "id", "appSecret": "sec"}, mode=0o600)
            self.assertTrue(path.exists())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["appId"], "id")
            mode = stat.S_IMODE(path.stat().st_mode)
            self.assertEqual(mode, 0o600)

    def test_non_credential_file_permissions(self):
        """非凭证文件可使用 644 权限。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            loader.safe_write_json(path, {"default_identity": "user"}, mode=0o644)
            mode = stat.S_IMODE(path.stat().st_mode)
            self.assertEqual(mode, 0o644)


class TestCredentialsFallback(unittest.TestCase):
    def test_load_credentials_data_uses_resolver_path(self):
        """未指定 path 时使用 resolver 解析的 credentials.json。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.environ.pop(loader.FEISHU_CONFIG_DIR_ENV, None)
            try:
                os.environ[loader.FEISHU_CONFIG_DIR_ENV] = tmpdir
                creds_path = Path(tmpdir) / "credentials.json"
                creds_path.write_text(
                    json.dumps({"appId": "a", "appSecret": "s"}), encoding="utf-8"
                )
                data, resolved = loader.load_credentials_data()
                self.assertEqual(data["appId"], "a")
                self.assertEqual(resolved, creds_path)
            finally:
                if old is None:
                    os.environ.pop(loader.FEISHU_CONFIG_DIR_ENV, None)
                else:
                    os.environ[loader.FEISHU_CONFIG_DIR_ENV] = old


if __name__ == "__main__":
    unittest.main()
