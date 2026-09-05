class SMADevice:

    def __init__(self, name, dtype, ip, model=None, device_id=None):

        self.name = name
        self.type = dtype
        self.ip = ip
        self.model = model
        self.id = device_id or name


    def info(self):

        return {
            "name": self.name,
            "type": self.type,
            "model": self.model,
            "ip": self.ip
        }
