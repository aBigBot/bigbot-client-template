class SkillProvider:
    def __init__(self, *args, **kwargs):
        pass

    def oauth(self, binder, user_id, component, **kwargs):
        pass

    def on_execute(self, binder, user_id, package, data, *args, **kwargs):
        """Process skill. This method must be overrided.

        When the skill is processed succesfully the method shoudl return data that is going to be
        mixed with the Nodes defined in the property nodes of the skill block.

        Args:
            binder (main.Binder.Binder)
            user_id (int): Id of user interacting with the skill
            package (str): Package indetifier, e.g. "com.bits.wordpress.skill"
            data (dict): Skill state
            args (list): Contains a main.Statement.InputStatement if processor is managed by
                main.Block.InputSkill
            kwargs (dict): Extra arguments, the complete skill definition is passed here as
                {"skill": {skill_definition...}}.

        Returns:
            - False or None: If skill couldn't be processed.
            - Other: Depends on the nodes defined in the block.
        """
        pass

    # this method should return best possible search input value against query
    def on_query_search(self, binder, user_id, package, data, query, **kwargs):
        """ """
        pass

    # this method returns list of search result against query
    def on_search(self, binder, user_id, package, data, query, **kwargs):
        """Returns a list of suggestions based on a user query. This method must be overrided.

        This method is only called when the skill provider is wrapped in main.Block.InputSkill.

        Args:
            binder (main.Binder.Binder)
            user_id (int): Id of user interacting with the skill
            package (str): Package indetifier, e.g. "com.bits.wordpress.skill"
            data (dict): Skill state
            query (str): User query
            kwargs (dict): Extra arguments, the complete skill definition is passed here as
                {"skill": {skill_definition...}}.

        Returns:
            list: A list of main.Node.SearchNode. Build the results with the static method
                SearchNode.wrap_text(human_readeable_value, value) where human_readeable_value is a
                string, and value can be any type. human_redeable_value and value will be passed in
                a main.Statement.InputStatement as text and input respectevely.
        """
        pass

    def on_verify_input(self, binder, user_id, package, searchable, value, **kwargs):
        """Verify search input"""
        return True
