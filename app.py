from flask import Flask, render_template, request
import paramiko
import time
import re

app = Flask(__name__)

def provisionar_onu(nome_cliente):
    host = "10.11.104.2"
    port = 22
    user = "root"
    password = "berg88453649"

    resultado = f"Provisionando para cliente: {nome_cliente}\n\n"

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=host, port=port, username=user, password=password, timeout=10)
        shell = client.invoke_shell()
        time.sleep(1)

        resultado += "✅ Conectado à OLT\n"

        # Entrar no modo privilegiado/config
        def send_command(cmd, sleep=2):
            shell.send(cmd + "\n")
            time.sleep(sleep)
            output = ""
            while shell.recv_ready():
                output += shell.recv(65535).decode("utf-8")
            return output

        send_command("enable", 1)
        send_command("config", 1)

        # Detecta ONUs esperando provisionamento
        output = send_command("display ont autofind all", 5)
        resultado += output + "\n"

        pattern = re.compile(r"(\d+/\d+)\s+(\d+)\s+(\S+)")
        onus = pattern.findall(output)

        if not onus:
            resultado += "❌ Nenhuma ONU encontrada para provisionar.\n"
        else:
            resultado += f"✅ Encontradas {len(onus)} ONUs para provisionar.\n"
            # Só provisiona a primeira para exemplo
            interface, onu_id, sn = onus[0]
            resultado += f"Provisionando ONU na interface {interface}, ONU ID {onu_id}, SN {sn} ...\n"

            send_command(f"interface gpon {interface}")

            cmd_add = f"ont add {onu_id} sn-auth {sn} omcport {interface}/{onu_id}"
            resultado += f"Executando: {cmd_add}\n"
            resultado += send_command(cmd_add)

            # Comando exemplo de serviço (adicione o que precisar)
            cmd_profile = f"ont service-port add {onu_id} 1 vlan 100 gpon 0/1/{onu_id} gemport 1 multi-service user-vlan 100"
            resultado += f"Configurando serviço (exemplo): {cmd_profile}\n"
            resultado += send_command(cmd_profile)

            send_command("quit")

            sinal_cmd = f"display ont optical-info {interface} {onu_id}"
            resultado += f"Consultando sinal com: {sinal_cmd}\n"
            resultado += send_command(sinal_cmd, sleep=3)

        shell.close()
        client.close()
        resultado += "\n📝 Provisionamento finalizado."

    except Exception as e:
        resultado += f"\n❌ Erro: {e}"

    return resultado


@app.route("/", methods=["GET", "POST"])
def index():
    resultado = ""
    if request.method == "POST":
        nome_cliente = request.form.get("nome_cliente", "").strip()
        if nome_cliente:
            resultado = provisionar_onu(nome_cliente)
        else:
            resultado = "⚠️ Por favor, insira o nome do cliente."
    return render_template("index.html", resultado=resultado)


if __name__ == "__main__":
    app.run(debug=True)
