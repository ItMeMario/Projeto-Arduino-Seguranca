Este código é feito para rodar em um SO Linux Ubuntu ver 22

O código necessita que o Eyeflow esteja instalado

Para executar o programa  acesse a pasta /opt/eyeflow, basta usar cd /opt/eyeflow

Estando dentro da pasta eyeflow execute: ./edge_run.sh

Após o carregamento uma tela de debug irá abrir e você poderá acompanhar a I.A.

Mantenha o terminal aberto, fechar ele resultará no termino da aplicação também

Caso queira parar a aplicação va no terminal e use a combinação de teclas CTRL+C

Caso queira subir exemplos das imagens gravadas clique na tela de debug com o mouse e use a tecla Q
isto pode acabar travando a aplicação por um tempo e as vezes necessário reiniciar o programa



Caso a luz esteja acesa e queira desligar de forma manual use o comando em um navegador:

http://ip_do_plc/set_output?address=1&state=0

Para ligar ela manualmente: 

http://ip_do_plc/set_output?address=1&state=1


Se o programa estiver apresentando lentidão/estiver agindo de maneira que julgue inesperada tente:

No terminal onde a aplicação estiver rodando use o comando CTRL C para parar a aplicação e depois rode o comando ./edge_run.sh para reiniciar ela (certifique se de estar dentro da pasta /opt/eyeflow)


