__all__ = ('static_vars')

def static_vars(**kwargs):
    ''' Thanks to Claudiu and ony at https://stackoverflow.com/questions/279561/what-is-the-python-equivalent-of-static-variables-inside-a-function '''
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate
