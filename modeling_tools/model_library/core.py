"""Workshop starter-model library backend (Maya Python 3)."""
from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import maya.cmds as cmds


@dataclass(frozen=True)
class ModelAsset:
    name: str
    usd_path: Path
    icon_path: Path | None
    tags: tuple[str, ...]


class ModelLibrary:
    """USD models, JSON metadata, and parallel PNG icon library."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser()
        self.models = self.root / "models"
        self.icons = self.root / "icons"
        self.metadata = self.root / "metadata"

    def ensure_dirs(self):
        for directory in (self.models, self.icons, self.metadata):
            directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _stem(name: str) -> str:
        stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip()).strip("_")
        if not stem:
            raise ValueError("Asset name must contain letters or numbers")
        return stem

    def list_assets(self, search: str = "", tag: str | None = None) -> list[ModelAsset]:
        result = []
        if not self.models.exists():
            return result
        for usd in self.models.glob("*.usd"):
            meta_file = self.metadata / f"{usd.stem}.json"
            data = {}
            if meta_file.exists():
                try:
                    data = json.loads(meta_file.read_text(encoding="utf-8"))
                except (ValueError, OSError) as exc:
                    cmds.warning(f"Invalid model metadata {meta_file}: {exc}")
            name = str(data.get("name") or usd.stem)
            tags = tuple(str(t) for t in data.get("tags", []) if str(t).strip())
            icon = self.icons / f"{usd.stem}.png"
            if search.casefold() not in name.casefold() and not any(search.casefold() in t.casefold() for t in tags):
                continue
            if tag and tag != "All Tags" and not any(t.casefold() == tag.casefold() for t in tags):
                continue
            result.append(ModelAsset(name, usd, icon if icon.is_file() else None, tags))
        return sorted(result, key=lambda a: (a.name.casefold(), a.usd_path.stem))

    def all_tags(self) -> list[str]:
        return sorted({t for asset in self.list_assets() for t in asset.tags}, key=str.casefold)

    @staticmethod
    def _require_usd():
        if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
            cmds.loadPlugin("mayaUsdPlugin", quiet=True)
        if not hasattr(cmds, "mayaUSDExport") or not hasattr(cmds, "mayaUSDImport"):
            raise RuntimeError("Maya USD import/export commands are unavailable")

    def save(self, name: str, nodes: list[str] | None = None,
             tags: list[str] | None = None, overwrite: bool = False) -> ModelAsset:
        """Export a temporary duplicate, preserving original scene nodes.

        The temporary model is normalized to the world origin. Multiple selected
        roots become children of one temporary root; their relative layout remains.
        """
        self._require_usd()
        self.ensure_dirs()
        stem = self._stem(name)
        target = self.models / f"{stem}.usd"
        meta = self.metadata / f"{stem}.json"
        if not overwrite and (target.exists() or meta.exists()):
            raise FileExistsError(f"Asset '{stem}' already exists")
        nodes = nodes if nodes is not None else (cmds.ls(selection=True, long=True, transforms=True) or [])
        nodes = list(dict.fromkeys(nodes))
        if not nodes:
            raise ValueError("Select at least one model transform")
        # Ignore selected descendants of other selected roots.
        roots = [n for n in nodes if not any(n.startswith(p + "|") for p in nodes if p != n)]
        previous_selection = cmds.ls(selection=True, long=True) or []
        temp_root = None
        tmp_file = None
        try:
            # Position export root at the first selected object's world matrix.
            # Parenting duplicates beneath it preserves their world poses, then
            # moving the root to identity normalizes the entire asset.
            anchor = cmds.xform(roots[0], query=True, worldSpace=True, matrix=True)
            temp_root = cmds.group(empty=True, name="__workshop_model_export__#")
            cmds.xform(temp_root, worldSpace=True, matrix=anchor)
            for node in roots:
                duplicate = cmds.duplicate(node, renameChildren=True, returnRootsOnly=True)[0]
                cmds.parent(duplicate, temp_root)
            cmds.xform(temp_root, worldSpace=True, matrix=[1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1])
            cmds.select(temp_root, replace=True)
            fd, tmp_file = tempfile.mkstemp(suffix=".usd", dir=str(self.models))
            os.close(fd)
            # Polygonal scheme is essential: USD ignores authored face-varying
            # normals on Catmull-Clark subdivision meshes.
            cmds.mayaUSDExport(
                file=tmp_file,
                selection=True,
                defaultMeshScheme="none",
                exportUVs=True,
            )
            if not Path(tmp_file).is_file() or Path(tmp_file).stat().st_size == 0:
                raise RuntimeError("Maya USD export did not produce an asset")
            os.replace(tmp_file, target)
            tmp_file = None
            clean_tags = sorted({t.strip() for t in (tags or []) if t.strip()}, key=str.casefold)
            meta.write_text(json.dumps({"name": name.strip(), "tags": clean_tags}, indent=2), encoding="utf-8")
            return ModelAsset(name.strip(), target, self.icons / f"{stem}.png" if (self.icons / f"{stem}.png").exists() else None, tuple(clean_tags))
        finally:
            if temp_root and cmds.objExists(temp_root):
                cmds.delete(temp_root)
            if tmp_file and os.path.exists(tmp_file):
                os.unlink(tmp_file)
            cmds.select([n for n in previous_selection if cmds.objExists(n)], replace=True)

    @staticmethod
    def _import_usd(path: Path) -> str:
        """Import a library asset without retaining the USD export wrappers.

        One geometry root becomes one Maya transform. Multiple selected roots
        become a single *meaningful* group, preserving their relative layout.
        """
        ModelLibrary._require_usd()
        before = set(cmds.ls(assemblies=True, long=True) or [])
        cmds.mayaUSDImport(file=str(path))
        after = set(cmds.ls(assemblies=True, long=True) or [])
        roots = sorted(after - before)
        if not roots:
            raise RuntimeError(f"USD import created no top-level transforms: {path}")

        def unwrap(nodes: list[str]) -> list[str]:
            """Remove known temporary export/group wrappers only."""
            result = []
            for node in nodes:
                leaf = node.rsplit("|", 1)[-1]
                # Maya USD may sanitize double underscores to single underscores.
                is_export_wrapper = (
                    "workshop_model_export" in leaf.lower()
                    or leaf.lower().startswith("__workshop_model_export")
                )
                children = cmds.listRelatives(node, children=True, fullPath=True,
                                              type="transform") or []
                shapes = cmds.listRelatives(node, shapes=True, fullPath=True) or []
                if is_export_wrapper and children and not shapes:
                    children = cmds.parent(children, world=True)
                    cmds.delete(node)
                    result.extend(unwrap(cmds.ls(children, long=True) or []))
                else:
                    result.append(node)
            return result

        try:
            # mayaUSDImport usually adds a container named for the file itself.
            # Strip it only when the contents clearly contain our export wrapper.
            expanded = []
            for root in roots:
                children = cmds.listRelatives(root, children=True, fullPath=True,
                                              type="transform") or []
                shapes = cmds.listRelatives(root, shapes=True, fullPath=True) or []
                if (not shapes and children and
                    any("workshop_model_export" in c.lower() for c in children)):
                    children = cmds.parent(children, world=True)
                    cmds.delete(root)
                    expanded.extend(cmds.ls(children, long=True) or [])
                else:
                    expanded.append(root)
            actual_roots = unwrap(expanded)
            if len(actual_roots) == 1:
                return cmds.rename(actual_roots[0], f"{path.stem}#")
            group = cmds.group(empty=True, name=f"{path.stem}#")
            cmds.parent(actual_roots, group)
            return group
        except Exception:
            # A failed cleanup must never delete unrelated preexisting objects.
            raise

    def place(self, asset: ModelAsset, mode: str = "At Origin",
              targets: list[str] | None = None) -> list[str]:
        """Import at origin, match each selected transform, or replace each target.

        Replacement is destructive only after successful import and matrix match.
        Maya's undo chunk groups the entire operation for easy undo.
        """
        if mode not in {"At Origin", "At Selected", "Replace Selected"}:
            raise ValueError(f"Unsupported placement mode: {mode}")
        targets = targets if targets is not None else (cmds.ls(selection=True, long=True, transforms=True) or [])
        if mode != "At Origin" and not targets:
            raise ValueError(f"'{mode}' requires selected transforms")
        if mode == "Replace Selected":
            for target in targets:
                if cmds.referenceQuery(target, isNodeReferenced=True) or cmds.lockNode(target, query=True, lock=True)[0]:
                    raise RuntimeError(f"Cannot replace referenced or locked node: {target}")
        results = []
        cmds.undoInfo(openChunk=True, chunkName="Workshop Place Model")
        try:
            for target in (targets if mode != "At Origin" else [None]):
                matrix = cmds.xform(target, query=True, worldSpace=True, matrix=True) if target else None
                model = self._import_usd(asset.usd_path)
                if matrix:
                    cmds.xform(model, worldSpace=True, matrix=matrix)
                results.append(model)
            # Do not delete originals until every replacement succeeded.
            if mode == "Replace Selected":
                cmds.delete(targets)
            cmds.select(results, replace=True)
            return results
        finally:
            cmds.undoInfo(closeChunk=True)
