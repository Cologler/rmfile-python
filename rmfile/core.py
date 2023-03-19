# -*- coding: utf-8 -*-
# 
# Copyright (c) 2023~2999 - Cologler <skyoflw@gmail.com>
# ----------
# 
# ----------

import os
import io
import abc
import typing
import pathlib
import hashlib
from contextlib import suppress

import typer
import rich
import atomicwrites
import xlgcid
import send2trash


class TestContext:
    def __init__(self, path: str) -> None:
        self.path = path
        self.hashs: dict[str, str] = {}

class ContentHasher(typing.Protocol):
    name: str
    def update(self, buf) -> None: ...
    def digest(self) -> bytes: ...

class TestSet(abc.ABC):
    def __init__(self, name: str, lines: list[str]) -> None:
        self.name = name
        self._dataset = self._parpare_set(lines)
        self._adding_rows: set[str] = set()

    def adding_rows(self):
        return list(self._adding_rows)

    def all_rows(self):
        return list(sorted(self._dataset | self._adding_rows))

    def _parpare_set(self, lines: list[str]) -> set[str]:
        s = {line.strip() for line in lines}
        s.discard('')
        return s

    def _read_value(self, ctx: TestContext):
        raise NotImplementedError

    def test(self, ctx: TestContext):
        return self._read_value(ctx) in self._dataset

    def add(self, ctx: TestContext):
        if (value := self._read_value(ctx)) not in self._dataset:
            self._adding_rows.add(value)

    @property
    def is_test_content(self):
        return False

    def get_buffer_size(self, path: str) -> int | None:
        return None

    def get_content_hasher(self) -> ContentHasher:
        raise NotImplementedError


class NameTestSet(TestSet):
    def _read_value(self, ctx: TestContext):
        return os.path.basename(ctx.path)


class INameTestSet(TestSet):
    def _parpare_set(self, lines: list[str]) -> set[str]:
        s = super()._parpare_set(lines)
        return {x.lower() for x in s}

    def _read_value(self, ctx: TestContext):
        return os.path.basename(ctx.path).lower()


class Sha1TestSet(TestSet):
    def _parpare_set(self, lines: list[str]) -> set[str]:
        s = super()._parpare_set(lines)
        return {x.lower() for x in s}

    def _read_value(self, ctx: TestContext):
        return ctx.hashs['sha1'].lower()

    @property
    def is_test_content(self):
        return True

    def get_content_hasher(self):
        return hashlib.sha1()


class GcidTestSet(TestSet):
    def _parpare_set(self, lines: list[str]) -> set[str]:
        s = super()._parpare_set(lines)
        return {x.lower() for x in s}

    def _read_value(self, ctx: TestContext):
        return ctx.hashs[_GcidHasher.name].lower()

    @property
    def is_test_content(self):
        return True

    def get_buffer_size(self, path: str):
        return xlgcid.get_gcid_piece_size(os.path.getsize(path))

    def get_content_hasher(self):
        return _GcidHasher()


class _GcidHasher:
    name: str = 'gcid'

    def __init__(self) -> None:
        self.__isha1 = hashlib.sha1()

    def update(self, buf):
        self.__isha1.update(hashlib.sha1(buf).digest())

    def digest(self):
        return self.__isha1.digest()


class TestSets:
    def __init__(self, tests_sets: list[TestSet]) -> None:
        self.__tests_sets = tests_sets
        self.__metadata_tests_sets = tuple(ts for ts in self.__tests_sets if not ts.is_test_content)
        self.__content_tests_sets = tuple(ts for ts in self.__tests_sets if ts.is_test_content)

    @property
    def tests_sets(self):
        return self.__tests_sets.copy()

    def __context_fill_hashs(self, ctx: TestContext):
        if tss := self.__content_tests_sets:
            buf_sizes = [bz for bz in (ts.get_buffer_size(ctx.path) for ts in tss) if bz]
            if buf_sizes:
                assert len(buf_sizes) == 1, 'TODO'
                buf_size = buf_sizes[0]
            else:
                buf_size = io.DEFAULT_BUFFER_SIZE

            hashers = tuple(ts.get_content_hasher() for ts in tss)

            buf = bytearray(buf_size)  # Reusable buffer to reduce allocations.
            buf_view = memoryview(buf)
            with open(ctx.path, 'rb') as fp:
                while read_size := fp.readinto(buf):
                    [h.update(buf_view[:read_size]) for h in hashers]

            for h in hashers:
                ctx.hashs[h.name] = h.digest().hex().lower()

    def test(self, path: str):
        ctx: TestContext = TestContext(path)
        assert self.__tests_sets

        # test by metadata
        if not all(ts.test(ctx) for ts in self.__metadata_tests_sets):
            return False

        # test by content
        self.__context_fill_hashs(ctx)
        if not all(ts.test(ctx) for ts in self.__content_tests_sets):
            return False

        return True

    def add(self, path: str):
        ctx: TestContext = TestContext(path)
        assert self.__tests_sets

        self.__context_fill_hashs(ctx)
        [ts.add(ctx) for ts in self.__tests_sets]


app = typer.Typer()

@app.command()
def main(
        location: str = typer.Argument(..., help='The dir or file to remove.'),
        name    : str = typer.Option(None, help="Load name patterns from file"),
        iname   : str = typer.Option(None, help="Same as --name, but case-insensitive"),
        sha1    : str = typer.Option(None, help='Load sha1 patterns from file'),
        gcid    : str = typer.Option(None, help='Load gcid patterns from file'),
        from_dir: str = typer.Option(None, envvar='RMFILE_FROM_DIR',
            help='Load patterns from dir (e.g. sha1.txt)'),
        dry_run : bool = typer.Option(False, "--dry-run"),
        add     : bool = typer.Option(False, "--add", help='add patterns to file from dir'),
    ):
    """
    Remove files based on patterns.
    """

    test_sets: list[TestSet] = []

    def load_from(value: str | None, set_type: typing.Type[TestSet], by_file: bool):
        if not value:
            return
        if os.path.isfile(value):
            lines = pathlib.Path(value).read_text('utf-8').splitlines()
        elif by_file:
            lines = []
        else:
            return
        test_sets.append(set_type(value, lines))

    load_from(name, NameTestSet, True)
    load_from(iname, INameTestSet, True)
    load_from(sha1, Sha1TestSet, True)
    load_from(gcid, GcidTestSet, True)

    if from_dir:
        load_from(os.path.join(from_dir, 'name.txt'), NameTestSet, False)
        load_from(os.path.join(from_dir, 'iname.txt'), INameTestSet, False)
        load_from(os.path.join(from_dir, 'sha1.txt'), Sha1TestSet, False)
        load_from(os.path.join(from_dir, 'gcid.txt'),  GcidTestSet, False)

    if not test_sets:
        return typer.echo('No pattern input.', err=True)

    tss = TestSets(test_sets)

    with suppress(OSError):
        walker = [('', [''], [location])] if os.path.isfile(location) else os.walk(location)
        to_remove = []
        for dirpath, _, filenames in walker:
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    if add:
                        tss.add(path)

                    else: # remove mode
                        if tss.test(path):
                            typer.echo(f'Remove: {path}')
                            if not dry_run:
                                to_remove.append(path)
                                send2trash.send2trash(path)
                except Exception as e:
                    typer.echo(e, err=True)
        if to_remove and not dry_run:
            send2trash.send2trash(to_remove)

    for ts in tss.tests_sets:
        if adding_rows := ts.adding_rows():
            rich.print(f'--- Rows added to [green] {ts.name} [/green] ---')
            for row in adding_rows:
                typer.echo(f'  {row}')
            if not dry_run:
                with atomicwrites.atomic_write(ts.name, mode='wb', overwrite=True) as f:
                    f.write(
                        '\n'.join(ts.all_rows()).encode('utf-8')
                    )

if __name__ == "__main__":
    app()
