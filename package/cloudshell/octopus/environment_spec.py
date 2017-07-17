class EnvironmentSpec:
    def __init__(self, name, description, sort_order, use_guided_failure=False):
        """
        :param name: The name of this environment. This should be short, preferably 5-20 characters.
        :param description: A short description of this environment that can be used to explain the purpose of the
        environment to other users. This field may contain markdown.
        :param sort_order: A number indicating the priority of this environment in sort order. Environments with a lower
         sort order will appear in the UI before items with a higher sort order.
        :param use_guided_failure: If set to true, deployments will prompt for manual intervention (Fail/Retry/Ignore)
        when failures are encountered in activities that support it. May be overridden with the Octopus.UseGuidedFailure
         special variable.
        :type name: str
        :type description: str
        :type sort_order: int
        :type use_guided_failure: bool
        """
        self._name = name
        self._description = description
        self._sort_order = sort_order
        self._use_guided_failure = use_guided_failure

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    @property
    def sort_order(self):
        return self._sort_order

    @property
    def use_guided_failure(self):
        return self._use_guided_failure

    @property
    def json(self):
        return {
            'Name': self.name,
            'Description': self.description,
            'SortOrder': self.sort_order,
            'UseGuidedFailure': self.use_guided_failure
        }

    def validate(self):
        if not self._name or \
                        len(self._name) > 20 or len(self._name) < 5:
            raise ValueError('EnvironmentSpec name must be between 5 and 20 characters')

        return True

    def set_id(self, id):
        self.id = id

    @staticmethod
    def from_dict(environment_dict):
        a = EnvironmentSpec(environment_dict['_name'],
                            environment_dict['_description'],
                            environment_dict['_sort_order'],
                            environment_dict['_use_guided_failure'])
        a.id = environment_dict['id']
        return a
