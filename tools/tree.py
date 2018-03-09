
class mTree(object):
    # def build_tree(root, node_list):
    #     # list to deep dict
    #     # [1, 2, 3, 4, 5] -> {1: {2: {3: {4: 5}}}}
    #     assert len(node_list) >= 2
    #     if len(node_list) > 2:
    #         node = node_list[0]
    #         if node not in root.keys():
    #             root[node] = dict()
    #         build_tree(root[node], node_list[1:])
    #     else:
    #         root[node_list[0]] = node_list[1]

    # def check_depth(selfroot, node_list):
    #     assert len(node_list) >= 2
    #
    #     ns = node_list[0]
    #     if not isinstance(ns, (tuple, list)):
    #         ns = [ns]
    #
    #     for node in ns:
    #         print("eTree check", root, node_list)
    #         if len(node_list) > 2:
    #             if node not in root.keys():
    #                 return len(node_list)
    #             else:
    #                 return mTree.check_depth(root[node], node_list[1:])
    #         else:
    #             if node in root.keys():
    #                 if isinstance(root[node], dict):
    #                     return -1
    #                 else:
    #                     return 0
    #             else:
    #                 return 2

    @staticmethod
    def build(root, node_list, secure=True):
        # list to deep dict
        # [1, 2, 3, 4, 5] -> {1: {2: {3: {4: 5}}}}
        # [1,2,('a','b'),4,5,6] -> {1: {2: {'a': {4: {5: 6}}, 'b': {4: {5: 6}}}}}
        assert len(node_list) >= 2

        ns = node_list[0]
        if not isinstance(ns, (tuple, list)):
            ns = [ns]

        for node in ns:
            print("eTree Build: root{}, node_list{}".format(root, node_list))
            if len(node_list) > 2:
                if node not in root.keys():
                    root[node] = dict()

                if isinstance(root[node], dict):
                    mTree.build(root[node], node_list[1:])
                else:
                    print("eTree Build", "root is not dict", root, list)
            else:
                assert isinstance(root, dict)
                if node in root.keys():
                    if isinstance(root[node], dict):    # root also reach the deepest level
                        print("eTree Build", "root is deeper than list", root, list)
                        return
                #update or create new value
                root[node] = node_list[1]

    @staticmethod
    def get_branch(root, node_list):
        node = node_list[0]
        if node in root.keys():
            if len(node_list) == 1:
                return root
            else:
                return mTree.get_branch(root[node], node_list[1:])
        else:
            #print('eTree get_branch', "node list '{}' not in root{}".format(node, root))
            pass

    @staticmethod
    def get_leaf_value(root, node_list):
        branch = mTree.get_branch(root, node_list)
        if branch:
            _, value = branch
            if isinstance(value, dict): # root also reach the deepest level
                print('eTree get_leaf_value', "root '{}' deeper than list".format(value))
            else:
                return value

    def get_nested_branch(root, node_list, r_type='d'):
        ns = node_list[0]
        if not isinstance(ns, (tuple, list)):
            ns = [ns]

        result = []
        for node in ns:
            if isinstance(root, dict):
                if node in root.keys():
                    if len(node_list) == 1:
                        value = root[node]
                        if not isinstance(value, dict):
                            if r_type == 'd':
                                result.append(root)
                            else:
                                result.append(value)
                        else:
                            print('eTree get_nested_branch', "root '{}' deeper than list".format(value))
                    else:
                        r = mTree.get_nested_branch(root[node], node_list[1:], r_type)
                        if r:
                            result.extend(r)
                else:
                    #print('eTree get_nested_branch', "node list '{}' not in root{}".format(node, root))
                    pass
            else:
                print('eTree get_nested_branch', "node list '{}' deeper than root". format(node))

        if result:  # return not []
            return result

    @staticmethod
    def get_nested_leaf_value(root, node_list):
        result = mTree.get_nested_branch(root, node_list, 'v')
        if result and len(result) == 1:
            result = result[0]

        return result

    # @staticmethod
    # def get_nested_leaf_value(root, node_list):
    #     ns = node_list[0]
    #     if not isinstance(ns, (tuple, list)):
    #         ns = [ns]
    #
    #     result = []
    #     for node in ns:
    #         if node in root.keys():
    #             if len(node_list) == 1:
    #                 value = root[node]
    #                 if not isinstance(value, dict):
    #                     result.append(value)
    #             else:
    #                 r = mTree.get_nested_leaf_value(root[node], node_list[1:])
    #                 if r:
    #                     result.extend(r)
    #     if result:
    #         return result