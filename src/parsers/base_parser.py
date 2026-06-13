class BaseParser:
    def parse(self, json_data) -> list:
        raise NotImplementedError("Each parser must implement parse()")
