def gateway_factory(name):
    if name == 'AimGateway':
        import authorizenet
        return authorizenet.AimGateway()
    if name == 'AimEmulationGateway':
        import quantam
        return quantam.AimEmulationGateway()
    if name == 'XmlMessengerGateway':
        import psigate
        return psigate.XmlMessengerGateway()
