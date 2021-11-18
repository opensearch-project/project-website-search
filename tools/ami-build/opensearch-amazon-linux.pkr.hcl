packer {
  required_plugins {
    amazon = {
      version = ">= 0.0.2"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

//https://www.packer.io/docs/builders/amazon/ebs#ami-configuration
source "amazon-ebs" "amazon-linux-2" {
  ami_name      = "opensearch-1.0.0"
  instance_type = "m5.large"
  region        = "us-west-2"
  source_ami    = "ami-0c2d06d50ce30b442"
  ssh_username  = "ec2-user"
}

build {
  name = "create-opensearch-ami"
  sources = [
    "source.amazon-ebs.amazon-linux-2"
  ]

  provisioner "shell" {
    script = "install.sh"
  }

  provisioner "file" {
    source      = "bootstrap.py"
    destination = "/home/ec2-user/scripts/bootstrap.py"
  }

  provisioner "file" {
    source      = "opensearch.sh"
    destination = "/home/ec2-user/scripts/opensearch.sh"
  }

  provisioner "file" {
    source      = "opensearch-dashboards.sh"
    destination = "/home/ec2-user/scripts/opensearch-dashboards.sh"
  }

  provisioner "file" {
    source      = "opensearch.service"
    destination = "/home/ec2-user/opensearch/systemd/opensearch.service"
  }

  provisioner "file" {
    source      = "opensearch-dashboards.service"
    destination = "/home/ec2-user/opensearch-dashboards/systemd/opensearch-dashboards.service"
  }

  provisioner "shell" {
    inline = [
      "sudo ln -s /home/ec2-user/opensearch/systemd/opensearch.service /usr/lib/systemd/system/opensearch.service",
      "sudo ln -s /home/ec2-user/opensearch-dashboards/systemd/opensearch-dashboards.service /usr/lib/systemd/system/opensearch-dashboards.service",
      "sudo /bin/systemctl daemon-reload",
      "sudo /bin/systemctl enable opensearch.service",
      "sudo /bin/systemctl enable opensearch-dashboards.service",
    ]
  }
}