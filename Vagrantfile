Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu"
  config.vm.network :forwarded_port, guest: 6379, host: 6379
  # Set virtual machine memory size
  config.vm.provider :virtualbox do |vbox|
    vbox.customize ["modifyvm", :id, "--memory", 1024]
  end
  config.vm.provision :shell, :path => ".vagrant/init.sh"
end