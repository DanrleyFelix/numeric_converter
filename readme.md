# Falta:
# QActions logo abaixo
# Salvar context específico-> Usa-se File -> Save Context (arquivo json)
# Carregar context específico-> Usa-se File -> Load Context (arquivo json)
# Salvar Logs específicos -> Usa-se File -> Save Log
# Carregar Logs específicos -> Usa-se File -> Load Log 
# Há o default context e default log que são salvamentos automáticos (representam o que usuário fez pela última fez no programa)
# Criar os contratos de acesso entre a UI e o Presenter
# Ocultar/Mostrar key panel em "preferences"
# Fazer as teclas da calculadora funcionar
# Criar um mini formulário para "preferences": radio button para key panel (true ou false) e outras opções além para: 
{
        "formatters": {
        "decimal": {
            "group_size": 3,
            "zero_pad": false
        },
        "binary": {
            "group_size": 8,
            "zero_pad": true
        },
        "hexBE": {
            "group_size": 2,
            "zero_pad": false
        },
        "hexLE": {
            "group_size": 4,
            "zero_pad": true
        }
    }
}
# criar uma documentação (ficará em helps) em html (css com dark themed navy). Pasta: helps (index.js, index.html, style.css, content.json). index.js traz o conteúdo do json para o html. 
# Finalizar o projeto tornando o conversor funcional (comunicação entre as camadas)