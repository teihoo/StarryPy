"""
Defines a common manager for plugins, which provide the bulk of the
functionality in StarryPy.
"""
import inspect
import os
import sys
from base_plugin import BasePlugin
from config import ConfigurationManager


class DuplicatePluginError(Exception):
    """
    Raised when there is a plugin of the same name/class already instantiated.
    """


class PluginNotFound(Exception):
    """
    Raised whenever a plugin can't be found from a given name.
    """


class MissingDependency(PluginNotFound):
    """
    Raised whenever there is a missing dependency during the loading
    of a plugin.
    """


class PluginManager(object):
    def __init__(self, base_class=BasePlugin):
        """
        Initializes the plugin manager. When called, with will first attempt
        to get the `ConfigurationManager` singleton and extract the core plugin
        path. After loading the core plugins with `self.load_plugins` it will
        do the same for plugins that may or may not have dependencies.

        :param base_class: The base class to use while searching for plugins.
        """
        self.plugins = []
        self.plugin_names = []
        self.config = ConfigurationManager()
        self.base_class = base_class

        self.core_plugin_dir = os.path.realpath(self.config.core_plugin_path)
        sys.path.append(self.core_plugin_dir)
        self.load_plugins(self.core_plugin_dir)

        self.plugin_dir = os.path.realpath(self.config.plugin_path)
        sys.path.append(self.plugin_dir)
        self.load_plugins(self.plugin_dir)

    def load_plugins(self, plugin_dir):
        """
        Loads and instantiates all classes deriving from `self.base_class`,
        though not `self.base_class` itself.

        :param plugin_dir: The directory to search for plugins.
        :return: None
        """
        for f in os.listdir(plugin_dir):
            if f.endswith(".py"):
                name = f[:-3]
            elif os.path.isdir(os.path.join(plugin_dir, f)):
                name = f
            else:
                continue
            try:
                mod = __import__(name, globals(), locals(), [], 0)
                for _, plugin in inspect.getmembers(mod, inspect.isclass):
                    if issubclass(plugin,
                                  self.base_class) and plugin is not self.base_class:
                        plugin_instance = plugin(self.config)
                        print plugin_instance.name
                        if plugin_instance.name in self.plugin_names:
                            continue
                        if plugin_instance.depends is not None:
                            for dependency in plugin_instance.depends:
                                try:
                                    dependency_instance = self.get_by_name(dependency)
                                except PluginNotFound:
                                    raise MissingDependency(dependency)
                                else:
                                    plugin_instance.plugins[dependency] = dependency_instance
                        self.plugins.append(plugin_instance)
            except ImportError as e:
                pass

    def activate_plugins(self):
        for plugin in self.plugins:
            plugin.activate()

    def deactivate_plugins(self):
        for plugin in self.plugins:
            plugin.deactivate()

    def do(self, protocol, command, data=None):
        """
        Runs a command across all currently loaded plugins.

        :param protocol: The protocol to insert into the plugin.
        :param command: The function name to run, passed as a string.
        :param data: The data to send to the function.

        :return: Whether or not all plugins returned True or None.
        :rtype: bool
        """
        return_values = []
        for plugin in self.plugins:
            plugin.protocol = protocol
            res = getattr(plugin, command, lambda _: True)(data)
            if res is None:
                res = True
            return_values.append(res)
        return all(return_values)

    def get_by_name(self, name):
        """
        Gets a plugin by name. Used for dependency checks, though it could
        be used for other purposes.

        :param name: The name of the plugin, defined in the class as `name`
        :return : The plugin in question or None.
        :rtype : BasePlugin subclassed instance.
        :raises : PluginNotFound
        """
        for plugin in self.plugins:
            print plugin.name
            print name
            print plugin.name == name
            if plugin.name.lower() == name.lower():
                return plugin
        raise PluginNotFound("No plugin with name=%s found." % name.lower())