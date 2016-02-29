# skytap_metadata set up a python script to allow us to
# collect the metadata json and make it available as facts in facter

class skytap_metadata {
    package { 'pyyaml':
        provider => 'pip',
        ensure   => 'installed',
    }

    file { 'skytap_metadata.py':
        ensure  => file,
        path    => '/etc/puppetlabs/facter/facts.d/skytap_metadata.py',
        owner   => 'root',
        group   => 'root',
        mode    => '0755',
        source  => 'puppet:///modules/skytap_metadata/skytap_metadata.py',
        require => Package['pyyaml'],
    }
}
