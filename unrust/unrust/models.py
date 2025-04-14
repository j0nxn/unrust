class Crate:
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.functions: list[Function] = []

    def __str__(self):
        result = f'''
/// CRATE: {self.name}@{self.version}
'''
        for function in self.functions:
            result += f'''
{function}
'''
        return result


class Function:
    def __init__(self, name):
        self.name = name
        self.unsafe = None
        self.source = None
        self.decompiles: list[str] = None

    def __str__(self):
        result = f'''
/// {'UNSAFE' if self.unsafe else 'SAFE'} FUNCTION: {self.name}
{self.source}
'''
        for id, decompile in enumerate(self.decompiles):
            result += f'''
/// DECOMPILE: {self.name}.{id}
{decompile}
'''
        return result
