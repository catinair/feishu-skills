#!/usr/bin/env python3
"""Tests for runtime config path resolver in _config_loader."""

import contextlib
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        # 真实项目路径大概率不是固定的工作区路径
        self.assertIsNone(loader._detect_platform_workspace())
        self.assertIsNone(loader.get_runtime_config_dir())

    def test_platform_workspace_detection(self):
        """模拟平台 workspace/skills/<skill>/ 结构时识别为平台。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            skill_root = workspace / "skills" / "feishu-skills"
            skill_root.mkdir(parents=True)
            runtime_dir = workspace / "runtime_assets" / "feishu-skills"

            original_skill_root = loader.SKILL_ROOT
            original_detect = loader._detect_platform_workspace
            try:
                loader.SKILL_ROOT = skill_root
                loader._detect_platform_workspace = lambda: workspace
                # 清空模块常量缓存
                loader.CONFIG_DIR = loader._compute_default_config_path("")
                loader.CREDENTIALS_FILE = loader._compute_default_config_path(
                    "credentials.json"
                )
                loader.SETTINGS_FILE = loader._compute_default_config_path(
                    "settings.json"
                )
                loader.PERMISSIONS_FILE = loader._compute_default_config_path(
                    "permissions.json"
                )
                loader.RISK_POLICY_FILE = loader._compute_default_config_path(
                    "risk_policy.json"
                )

                runtime = loader.get_runtime_config_dir()
                self.assertIsNotNone(runtime)
                self.assertEqual(runtime, runtime_dir)

                # for_write=True 应自动创建 runtime_assets 目录
                write_dir = loader.get_config_dir(for_write=True)
                self.assertTrue(write_dir.exists())
                self.assertEqual(write_dir, runtime_dir)

                # 写入应落到 runtime_assets
                write_path = loader.resolve_config_path(
                    "credentials.json", for_write=True
                )
                self.assertEqual(write_path, runtime_dir / "credentials.json")
            finally:
                loader.SKILL_ROOT = original_skill_root
                loader._detect_platform_workspace = original_detect
                loader.CONFIG_DIR = loader._compute_default_config_path("")
                loader.CREDENTIALS_FILE = loader._compute_default_config_path(
                    "credentials.json"
                )
                loader.SETTINGS_FILE = loader._compute_default_config_path(
                    "settings.json"
                )
                loader.PERMISSIONS_FILE = loader._compute_default_config_path(
                    "permissions.json"
                )
                loader.RISK_POLICY_FILE = loader._compute_default_config_path(
                    "risk_policy.json"
                )

    def test_opencode_config_dir_derives_workspace_from_skill_root(self):
        """企业空间下优先从 SKILL_ROOT 反向推导 workspace（存在可写 runtime_assets 时）。"""
        getenv_values = {
            "OPENCODE": "",
            "OPENCODE_CONFIG_DIR": "/home/user/.opencode",
        }

        original_skill_root = loader.SKILL_ROOT
        try:
            loader.SKILL_ROOT = Path("/home/user/.opencode/skills/feishu-skills")
            with patch.object(
                loader.os, "getenv", side_effect=lambda key: getenv_values.get(key)
            ):
                with patch.object(loader.os, "access", return_value=True):
                    with patch.object(loader.Path, "is_dir", return_value=True):
                        workspace = loader._detect_platform_workspace()
            # 新实现不再依赖 OPENCODE 门控：skill 位于 <workspace>/skills/feishu-skills，
            # workspace = SKILL_ROOT.parents[1]，且 runtime_assets 存在且可写时直接采用。
            self.assertEqual(workspace, Path("/home/user/.opencode"))
        finally:
            loader.SKILL_ROOT = original_skill_root


class TestGetConfigContext(unittest.TestCase):
    def test_local_returns_skill_root(self):
        ctx = loader.get_config_context()
        self.assertEqual(ctx["config_dir"], loader.SKILL_ROOT / "config")
        self.assertEqual(ctx["source"], "skill_root")
        self.assertFalse(ctx["is_platform"])

    def test_platform_returns_runtime_assets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            skill_root = workspace / "skills" / "feishu-skills"
            skill_root.mkdir(parents=True)
            runtime_dir = workspace / "runtime_assets" / "feishu-skills"

            original_skill_root = loader.SKILL_ROOT
            original_detect = loader._detect_platform_workspace
            try:
                loader.SKILL_ROOT = skill_root
                loader._detect_platform_workspace = lambda: workspace
                loader.CONFIG_DIR = loader._compute_default_config_path("")
                loader.CREDENTIALS_FILE = loader._compute_default_config_path(
                    "credentials.json"
                )
                loader.SETTINGS_FILE = loader._compute_default_config_path(
                    "settings.json"
                )
                loader.PERMISSIONS_FILE = loader._compute_default_config_path(
                    "permissions.json"
                )
                loader.RISK_POLICY_FILE = loader._compute_default_config_path(
                    "risk_policy.json"
                )

                ctx = loader.get_config_context()
                self.assertEqual(ctx["config_dir"], runtime_dir)
                self.assertEqual(ctx["source"], "platform_runtime_assets")
                self.assertTrue(ctx["is_platform"])
            finally:
                loader.SKILL_ROOT = original_skill_root
                loader._detect_platform_workspace = original_detect
                loader.CONFIG_DIR = loader._compute_default_config_path("")
                loader.CREDENTIALS_FILE = loader._compute_default_config_path(
                    "credentials.json"
                )
                loader.SETTINGS_FILE = loader._compute_default_config_path(
                    "settings.json"
                )
                loader.PERMISSIONS_FILE = loader._compute_default_config_path(
                    "permissions.json"
                )
                loader.RISK_POLICY_FILE = loader._compute_default_config_path(
                    "risk_policy.json"
                )

    def test_env_override_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = os.environ.pop(loader.FEISHU_CONFIG_DIR_ENV, None)
            try:
                os.environ[loader.FEISHU_CONFIG_DIR_ENV] = tmpdir
                ctx = loader.get_config_context()
                self.assertEqual(ctx["config_dir"], Path(tmpdir))
                self.assertEqual(ctx["source"], "env")
                self.assertFalse(ctx["is_platform"])
            finally:
                if old is None:
                    os.environ.pop(loader.FEISHU_CONFIG_DIR_ENV, None)
                else:
                    os.environ[loader.FEISHU_CONFIG_DIR_ENV] = old


class TestSafeWriteJson(unittest.TestCase):
    def test_atomic_write_and_permissions(self):
        """safe_write_json 应写入文件并设置 600 权限（credentials 场景）。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "credentials.json"
            loader.safe_write_json(
                path, {"appId": "id", "appSecret": "sec"}, mode=0o600
            )
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


@contextlib.contextmanager
def _platform_env(tmpdir):
    """模拟平台运行环境：skill-root 与 runtime_assets 分离。"""
    workspace = Path(tmpdir) / "workspace"
    skill_root = workspace / "skills" / "feishu-skills"
    skill_root.mkdir(parents=True)
    (skill_root / "config").mkdir(parents=True, exist_ok=True)
    runtime_dir = workspace / "runtime_assets" / "feishu-skills"

    original_skill_root = loader.SKILL_ROOT
    original_detect = loader._detect_platform_workspace
    try:
        loader.SKILL_ROOT = skill_root
        loader._detect_platform_workspace = lambda: workspace
        loader.CONFIG_DIR = loader._compute_default_config_path("")
        loader.CREDENTIALS_FILE = loader._compute_default_config_path(
            "credentials.json"
        )
        loader.SETTINGS_FILE = loader._compute_default_config_path("settings.json")
        loader.PERMISSIONS_FILE = loader._compute_default_config_path(
            "permissions.json"
        )
        loader.RISK_POLICY_FILE = loader._compute_default_config_path(
            "risk_policy.json"
        )
        yield workspace, skill_root, runtime_dir
    finally:
        loader.SKILL_ROOT = original_skill_root
        loader._detect_platform_workspace = original_detect
        loader.CONFIG_DIR = loader._compute_default_config_path("")
        loader.CREDENTIALS_FILE = loader._compute_default_config_path(
            "credentials.json"
        )
        loader.SETTINGS_FILE = loader._compute_default_config_path("settings.json")
        loader.PERMISSIONS_FILE = loader._compute_default_config_path(
            "permissions.json"
        )
        loader.RISK_POLICY_FILE = loader._compute_default_config_path(
            "risk_policy.json"
        )


class TestLoaderFallback(unittest.TestCase):
    def test_settings_prefers_canonical_over_skill_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with _platform_env(tmpdir) as (workspace, skill_root, runtime_dir):
                runtime_dir.mkdir(parents=True)
                (runtime_dir / "settings.json").write_text(
                    json.dumps({"brand": "canonical"}), encoding="utf-8"
                )
                (skill_root / "config" / "settings.json").write_text(
                    json.dumps({"brand": "fallback"}), encoding="utf-8"
                )
                data = loader.load_settings()
                self.assertEqual(data["brand"], "canonical")

    def test_settings_uses_skill_root_fallback_when_canonical_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with _platform_env(tmpdir) as (workspace, skill_root, runtime_dir):
                (skill_root / "config" / "settings.json").write_text(
                    json.dumps({"brand": "fallback"}), encoding="utf-8"
                )
                data = loader.load_settings()
                self.assertEqual(data["brand"], "fallback")

    def test_permissions_prefers_canonical_over_skill_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with _platform_env(tmpdir) as (workspace, skill_root, runtime_dir):
                runtime_dir.mkdir(parents=True)
                (runtime_dir / "permissions.json").write_text(
                    json.dumps({"scopes": {"tenant": ["t1"]}}), encoding="utf-8"
                )
                (skill_root / "config" / "permissions.json").write_text(
                    json.dumps({"scopes": {"tenant": ["t2"]}}), encoding="utf-8"
                )
                data = loader.load_permissions_config()
                self.assertEqual(data["scopes"]["tenant"], ["t1"])

    def test_permissions_uses_skill_root_fallback_when_canonical_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with _platform_env(tmpdir) as (workspace, skill_root, runtime_dir):
                (skill_root / "config" / "permissions.json").write_text(
                    json.dumps({"scopes": {"tenant": ["fallback"]}}), encoding="utf-8"
                )
                data = loader.load_permissions_config()
                self.assertEqual(data["scopes"]["tenant"], ["fallback"])

    def test_risk_policy_prefers_canonical_over_skill_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with _platform_env(tmpdir) as (workspace, skill_root, runtime_dir):
                runtime_dir.mkdir(parents=True)
                (runtime_dir / "risk_policy.json").write_text(
                    json.dumps(
                        {"workspace": {"trusted_folder_tokens": [{"token": "c1"}]}}
                    ),
                    encoding="utf-8",
                )
                (skill_root / "config" / "risk_policy.json").write_text(
                    json.dumps(
                        {"workspace": {"trusted_folder_tokens": [{"token": "f1"}]}}
                    ),
                    encoding="utf-8",
                )
                data = loader.load_risk_policy()
                self.assertEqual(
                    data["workspace"]["trusted_folder_tokens"][0]["token"], "c1"
                )

    def test_risk_policy_uses_skill_root_fallback_when_canonical_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with _platform_env(tmpdir) as (workspace, skill_root, runtime_dir):
                (skill_root / "config" / "risk_policy.json").write_text(
                    json.dumps(
                        {"workspace": {"trusted_folder_tokens": [{"token": "f1"}]}}
                    ),
                    encoding="utf-8",
                )
                data = loader.load_risk_policy()
                self.assertEqual(
                    data["workspace"]["trusted_folder_tokens"][0]["token"], "f1"
                )

    def test_credentials_prefers_canonical_over_skill_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with _platform_env(tmpdir) as (workspace, skill_root, runtime_dir):
                runtime_dir.mkdir(parents=True)
                (runtime_dir / "credentials.json").write_text(
                    json.dumps({"appId": "canonical", "appSecret": "s"}),
                    encoding="utf-8",
                )
                (skill_root / "config" / "credentials.json").write_text(
                    json.dumps({"appId": "fallback", "appSecret": "s"}),
                    encoding="utf-8",
                )
                data, path = loader.load_credentials_data()
                self.assertEqual(data["appId"], "canonical")
                self.assertEqual(path, runtime_dir / "credentials.json")

    def test_credentials_uses_skill_root_fallback_when_canonical_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with _platform_env(tmpdir) as (workspace, skill_root, runtime_dir):
                (skill_root / "config" / "credentials.json").write_text(
                    json.dumps({"appId": "fallback", "appSecret": "s"}),
                    encoding="utf-8",
                )
                data, path = loader.load_credentials_data()
                self.assertEqual(data["appId"], "fallback")
                self.assertEqual(path, skill_root / "config" / "credentials.json")

    def test_explicit_credentials_path_does_not_use_platform_fallback(self):
        """显式传入 credentials_path 且文件不存在时不应回退到 skill-root/legacy。"""
        env_keys = [
            "FEISHU_APP_ID",
            "FEISHU_APP_SECRET",
            "FEISHU_BRAND",
            "FEISHU_USER_ACCESS_TOKEN",
        ]
        old_values = {k: os.environ.pop(k, None) for k in env_keys}
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with _platform_env(tmpdir) as (workspace, skill_root, runtime_dir):
                    (skill_root / "config" / "credentials.json").write_text(
                        json.dumps({"appId": "fallback", "appSecret": "s"}),
                        encoding="utf-8",
                    )
                    explicit = Path(tmpdir) / "explicit.json"
                    with self.assertRaises(RuntimeError):
                        loader.load_credentials_data(str(explicit))
        finally:
            for k, v in old_values.items():
                if v is not None:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
