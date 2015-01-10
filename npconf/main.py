# -*- coding: utf-8 -*-

import logging
logger = logging.getLogger(__name__)
import os


def get_config_file(file):
    if hasattr(file, 'read'):
        pass
    elif isinstance(file, basestring) and os.path.exists(file):
        file = open(file, 'r')
    return file


class NPConfBaseException(Exception):
    ""


class NewAttributesNotAllowed(NPConfBaseException):
    ""


class ConfigSpace(dict):

    def __init__(self, owner):
        self._owner_ = owner
        super(ConfigSpace, self).__init__()
        self.__dict__ = self
        self._owner_ = owner

    def __getattribute__(self, name):
        value = object.__getattribute__(self, name)
        if name != '_owner_' and isinstance(value, ConfigValue):
            return value.store
        return value

    def check_strict(self, name):
        native_attrs = [
            '__dict__',
            '_owner_',
            '_orig_strict_',
            '_with_strict_',
        ]
        if name in native_attrs:
            return
        if self._owner_.strict and name not in self:
            raise NewAttributesNotAllowed('{0}: Creation of new attributes not permitted.'.format(repr(name)))

    def __setitem__(self, name, value):
        self.check_strict(name)
        dict.__setitem__(self, name, value)

    def __setattr__(self, name, value):
        self.check_strict(name)
        dict.__setattr__(self, name, value)

    def with_strict(self, strict):
        self._orig_strict_ = self._owner_.strict
        self._with_strict_ = strict
        return self

    def __enter__(self):
        self._owner_.strict = self._with_strict_  # see self.with_strict()
        return self

    def __exit__(self, *args, **kwargs):
        self._owner_.strict = self._orig_strict_
        del self._with_strict_  # see self.with_strict()


class ConfigValue(object):

    _root_instance = None

    def __init__(self, name, paths=[], data={}, strict=None):
        self._view = None
        self.name = name
        self.root_instance
        self.store = ConfigSpace(owner=self)
        self.claim_root()
        self.strict = strict
        if self.root_instance is self and self.strict is None:
            self.strict = True
        self.update(data)
        self.configure(paths, strict=False)

    def __setitem__(self, name, value):
        self.store[name] = value

    def update(self, data):
        self.store.update(data)

    def claim_root(self):
        if ConfigValue._root_instance is None:
            ConfigValue._root_instance = self

    @property
    def root_instance(self):
        return ConfigValue._root_instance

    @property
    def strict(self):
        if self._strict is None:
            return self.root_instance._strict
        else:
            return self._strict

    @strict.setter
    def strict(self, value):
        self._strict = value

    def __getattribute__(self, name):
        name_attr_value = object.__getattribute__(self, 'name')
        if name == name_attr_value:
            store = object.__getattribute__(self, 'store')
            setattr(self, name, store)
            return store
        return object.__getattribute__(self, name)

    @property
    def config(self):
        return self.store

    def configure(self, paths, strict=None):
        if isinstance(paths, basestring):
            paths = [paths]
        paths = [get_config_file(p) for p in paths]
        for file in paths:
            if strict is None:
                strict = self.strict
            env = {self.name: self.config}
            env.update(globals())
            with self.store.with_strict(strict):
                exec(file, env)
